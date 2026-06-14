// DropTarget.cpp : IDropTarget + IShellExtInit 实现
//
// 拦截文件拖拽到 Explorer 文件夹的操作，通过 Named Pipe 发送到 Python 后端
// 利用 IShellExtInit::Initialize() 获取目标文件夹路径

#include "stdafx.h"
#include "DropTarget.h"
#include "PipeClient.h"

// ── IShellExtInit ──────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE CFastFileOpDropTarget::Initialize(
    LPCITEMIDLIST pidlFolder,
    LPDATAOBJECT pDataObj,
    HKEY hkeyProgID)
{
    // Explorer 在创建 DragDropHandler 实例时调用此方法
    // pidlFolder 是用户拖拽文件到的目标文件夹的 PIDL
    m_targetFolder.clear();

    if (pidlFolder)
    {
        WCHAR szPath[MAX_PATH];
        if (SHGetPathFromIDListW(pidlFolder, szPath))
        {
            m_targetFolder = szPath;
        }
    }

    return S_OK;
}

// ── IDropTarget ────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE CFastFileOpDropTarget::DragEnter(
    IDataObject* pDataObj,
    DWORD grfKeyState,
    POINTL pt,
    DWORD* pdwEffect)
{
    m_canDrop = false;
    m_dropEffect = DROPEFFECT_NONE;

    if (!pdwEffect)
        return E_POINTER;

    // 检查 Python 服务是否在线
    if (!PipeClient::IsServiceOnline())
    {
        *pdwEffect = DROPEFFECT_NONE;
        return S_OK;
    }

    // 检查数据对象是否包含文件
    std::vector<std::wstring> files;
    if (GetDropFiles(pDataObj, files) && !files.empty())
    {
        m_canDrop = true;

        // 根据 Ctrl/Shift 键状态决定操作类型
        if (grfKeyState & MK_CONTROL)
        {
            m_dropEffect = DROPEFFECT_COPY;
        }
        else if (grfKeyState & MK_SHIFT)
        {
            m_dropEffect = DROPEFFECT_MOVE;
        }
        else
        {
            m_dropEffect = DROPEFFECT_COPY;
        }
    }

    *pdwEffect = m_dropEffect;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE CFastFileOpDropTarget::DragOver(
    DWORD grfKeyState,
    POINTL pt,
    DWORD* pdwEffect)
{
    if (!pdwEffect)
        return E_POINTER;

    if (m_canDrop)
    {
        if (grfKeyState & MK_CONTROL)
        {
            m_dropEffect = DROPEFFECT_COPY;
        }
        else if (grfKeyState & MK_SHIFT)
        {
            m_dropEffect = DROPEFFECT_MOVE;
        }
    }

    *pdwEffect = m_dropEffect;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE CFastFileOpDropTarget::DragLeave()
{
    m_canDrop = false;
    m_dropEffect = DROPEFFECT_NONE;
    m_targetFolder.clear();
    return S_OK;
}

HRESULT STDMETHODCALLTYPE CFastFileOpDropTarget::Drop(
    IDataObject* pDataObj,
    DWORD grfKeyState,
    POINTL pt,
    DWORD* pdwEffect)
{
    if (!pdwEffect)
        return E_POINTER;

    *pdwEffect = DROPEFFECT_NONE;

    if (!m_canDrop || m_targetFolder.empty())
        return S_OK;

    // 获取拖拽的文件列表
    std::vector<std::wstring> files;
    if (!GetDropFiles(pDataObj, files) || files.empty())
        return S_OK;

    // 确定操作类型
    std::wstring action;
    if (m_dropEffect == DROPEFFECT_MOVE)
    {
        action = L"move";
    }
    else
    {
        action = L"copy";
    }

    // 发送到 Python 处理
    bool success = SendToPython(action, files, m_targetFolder);

    if (success)
    {
        // 阻止系统默认拖放行为
        *pdwEffect = m_dropEffect;
    }

    m_canDrop = false;
    m_dropEffect = DROPEFFECT_NONE;

    return S_OK;
}

// ── 辅助函数 ──────────────────────────────────────────────────

bool CFastFileOpDropTarget::GetDropFiles(
    IDataObject* pDataObj,
    std::vector<std::wstring>& files)
{
    files.clear();

    if (!pDataObj)
        return false;

    FORMATETC fmt = { CF_HDROP, NULL, DVASPECT_CONTENT, -1, TYMED_HGLOBAL };
    STGMEDIUM stg;

    if (FAILED(pDataObj->GetData(&fmt, &stg)))
        return false;

    HDROP hDrop = static_cast<HDROP>(GlobalLock(stg.hGlobal));
    if (!hDrop)
    {
        ReleaseStgMedium(&stg);
        return false;
    }

    UINT count = DragQueryFileW(hDrop, 0xFFFFFFFF, NULL, 0);
    for (UINT i = 0; i < count; ++i)
    {
        WCHAR szFile[MAX_PATH];
        if (DragQueryFileW(hDrop, i, szFile, MAX_PATH) > 0)
        {
            files.push_back(szFile);
        }
    }

    GlobalUnlock(stg.hGlobal);
    ReleaseStgMedium(&stg);

    return !files.empty();
}

bool CFastFileOpDropTarget::SendToPython(
    const std::wstring& action,
    const std::vector<std::wstring>& src,
    const std::wstring& dst)
{
    std::wstring request = Utils::BuildJsonMessage(action, src, dst);
    std::wstring response;

    DWORD timeout = (action == L"delete") ?
        PIPE_OPERATION_TIMEOUT_DELETE : PIPE_OPERATION_TIMEOUT_COPY;

    if (PipeClient::SendRequest(request, response, timeout))
    {
        bool success = false;
        std::vector<std::wstring> failed;
        return Utils::ParseJsonResponse(response, success, failed) && success;
    }

    return false;
}
