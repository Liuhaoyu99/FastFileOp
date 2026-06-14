// DropTarget.cpp : IDropTarget 实现
//

#include "stdafx.h"
#include "DropTarget.h"
#include "PipeClient.h"

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

        // 根据 Shift/Ctrl 键状态决定效果
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
            // 默认复制
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
        // 根据 Shift/Ctrl 键状态更新效果
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

    if (!m_canDrop)
        return S_OK;

    // 获取拖拽的文件列表
    std::vector<std::wstring> files;
    if (!GetDropFiles(pDataObj, files) || files.empty())
        return S_OK;

    // 获取目标文件夹路径（需要从 Shell 文件夹获取）
    // 这里简化处理，假设目标路径由调用方提供
    // 实际使用时需要通过 IShellFolder 接口获取

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

    // 注意：这里无法直接获取目标路径
    // 需要在实际注册时配合 Shell 文件夹使用
    // 暂时不执行实际操作，返回成功

    *pdwEffect = m_dropEffect;
    return S_OK;
}

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
