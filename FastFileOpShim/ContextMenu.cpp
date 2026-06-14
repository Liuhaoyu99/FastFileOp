// ContextMenu.cpp : IContextMenu 实现
//

#include "stdafx.h"
#include "ContextMenu.h"
#include "PipeClient.h"

static const UINT ID_CMD_PASTE = 0;
static const UINT ID_CMD_MOVE_HERE = 1;

HRESULT STDMETHODCALLTYPE CFastFileOpContextMenu::Initialize(
    LPCITEMIDLIST pidlFolder,
    LPDATAOBJECT pDataObj,
    HKEY hkeyProgID)
{
    // 获取目标文件夹路径
    if (pidlFolder)
    {
        WCHAR szPath[MAX_PATH];
        if (SHGetPathFromIDListW(pidlFolder, szPath))
        {
            m_targetFolder = szPath;
        }
    }

    // 获取选中的文件列表
    if (pDataObj)
    {
        FORMATETC fmt = { CF_HDROP, NULL, DVASPECT_CONTENT, -1, TYMED_HGLOBAL };
        STGMEDIUM stg;

        if (SUCCEEDED(pDataObj->GetData(&fmt, &stg)))
        {
            HDROP hDrop = static_cast<HDROP>(GlobalLock(stg.hGlobal));
            if (hDrop)
            {
                UINT count = DragQueryFileW(hDrop, 0xFFFFFFFF, NULL, 0);
                for (UINT i = 0; i < count; ++i)
                {
                    WCHAR szFile[MAX_PATH];
                    if (DragQueryFileW(hDrop, i, szFile, MAX_PATH) > 0)
                    {
                        m_selectedFiles.push_back(szFile);
                    }
                }
                GlobalUnlock(stg.hGlobal);
            }
            ReleaseStgMedium(&stg);
        }
    }

    return S_OK;
}

HRESULT STDMETHODCALLTYPE CFastFileOpContextMenu::QueryContextMenu(
    HMENU hmenu,
    UINT indexMenu,
    UINT idCmdFirst,
    UINT idCmdLast,
    UINT uFlags)
{
    // 只在文件夹背景右键时显示
    if ((uFlags & CMF_DEFAULTONLY) || m_targetFolder.empty())
        return MAKE_HRESULT(SEVERITY_SUCCESS, FACILITY_NULL, 0);

    // 检查剪贴板是否有文件
    std::vector<std::wstring> clipboardFiles;
    bool hasClipboardFiles = GetClipboardFiles(clipboardFiles);

    if (!hasClipboardFiles)
        return MAKE_HRESULT(SEVERITY_SUCCESS, FACILITY_NULL, 0);

    // 检查 Python 服务是否在线
    if (!PipeClient::IsServiceOnline())
        return MAKE_HRESULT(SEVERITY_SUCCESS, FACILITY_NULL, 0);

    // 添加菜单项
    UINT idCmd = idCmdFirst;

    // 检查剪贴板是否为剪切操作
    bool isCut = false;
    if (OpenClipboard(NULL))
    {
        UINT cfFormat = RegisterClipboardFormatW(L"Preferred DropEffect");
        if (cfFormat)
        {
            HANDLE hData = GetClipboardData(cfFormat);
            if (hData)
            {
                DWORD* pdwEffect = static_cast<DWORD*>(GlobalLock(hData));
                if (pdwEffect)
                {
                    isCut = (*pdwEffect & DROPEFFECT_MOVE) != 0;
                    GlobalUnlock(hData);
                }
            }
        }
        CloseClipboard();
    }

    if (isCut)
    {
        InsertMenuW(hmenu, indexMenu, MF_BYPOSITION | MF_STRING,
                    idCmdFirst + ID_CMD_MOVE_HERE, L"移动到这里 (FastFileOp)");
    }
    else
    {
        InsertMenuW(hmenu, indexMenu, MF_BYPOSITION | MF_STRING,
                    idCmdFirst + ID_CMD_PASTE, L"粘贴 (FastFileOp)");
    }

    return MAKE_HRESULT(SEVERITY_SUCCESS, FACILITY_NULL, 1);
}

HRESULT STDMETHODCALLTYPE CFastFileOpContextMenu::InvokeCommand(
    CMINVOKECOMMANDINFO* pici)
{
    if (!pici)
        return E_INVALIDARG;

    // 检查是否为字符串命令
    if (HIWORD(pici->lpVerb) != 0)
    {
        // 字符串 verb
        if (_wcsicmp(pici->lpVerb, L"paste") == 0 ||
            _wcsicmp(pici->lpVerb, L"pastefastfileop") == 0)
        {
            // 执行粘贴
            std::vector<std::wstring> clipboardFiles;
            if (GetClipboardFiles(clipboardFiles) && !clipboardFiles.empty())
            {
                // 检查是否为剪切
                bool isCut = false;
                if (OpenClipboard(NULL))
                {
                    UINT cfFormat = RegisterClipboardFormatW(L"Preferred DropEffect");
                    if (cfFormat)
                    {
                        HANDLE hData = GetClipboardData(cfFormat);
                        if (hData)
                        {
                            DWORD* pdwEffect = static_cast<DWORD*>(GlobalLock(hData));
                            if (pdwEffect)
                            {
                                isCut = (*pdwEffect & DROPEFFECT_MOVE) != 0;
                                GlobalUnlock(hData);
                            }
                        }
                    }
                    CloseClipboard();
                }

                std::wstring action = isCut ? L"move" : L"copy";
                SendToPython(action, clipboardFiles, m_targetFolder);
            }
            return S_OK;
        }
        return E_FAIL;
    }

    // 数字命令 ID
    switch (LOWORD(pici->lpVerb))
    {
    case ID_CMD_PASTE:
    case ID_CMD_MOVE_HERE:
        {
            std::vector<std::wstring> clipboardFiles;
            if (GetClipboardFiles(clipboardFiles) && !clipboardFiles.empty())
            {
                std::wstring action = (LOWORD(pici->lpVerb) == ID_CMD_MOVE_HERE) ? L"move" : L"copy";
                SendToPython(action, clipboardFiles, m_targetFolder);
            }
        }
        return S_OK;
    }

    return E_FAIL;
}

HRESULT STDMETHODCALLTYPE CFastFileOpContextMenu::GetCommandString(
    UINT_PTR idCmd,
    UINT uFlags,
    UINT* pwReserved,
    LPSTR pszName,
    UINT cchMax)
{
    switch (idCmd)
    {
    case ID_CMD_PASTE:
        if (uFlags == GCS_HELPTEXTW)
        {
            wcscpy_s(reinterpret_cast<LPWSTR>(pszName), cchMax, L"使用 FastFileOp 粘贴文件");
            return S_OK;
        }
        break;
    case ID_CMD_MOVE_HERE:
        if (uFlags == GCS_HELPTEXTW)
        {
            wcscpy_s(reinterpret_cast<LPWSTR>(pszName), cchMax, L"使用 FastFileOp 移动文件");
            return S_OK;
        }
        break;
    }
    return E_INVALIDARG;
}

bool CFastFileOpContextMenu::GetClipboardFiles(std::vector<std::wstring>& files)
{
    files.clear();

    if (!OpenClipboard(NULL))
        return false;

    HDROP hDrop = static_cast<HDROP>(GetClipboardData(CF_HDROP));
    if (!hDrop)
    {
        CloseClipboard();
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

    CloseClipboard();
    return !files.empty();
}

bool CFastFileOpContextMenu::SendToPython(
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
