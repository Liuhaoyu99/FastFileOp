// ExplorerCommand.cpp : IExplorerCommand 实现
//

#include "stdafx.h"
#include "ExplorerCommand.h"
#include "PipeClient.h"

HRESULT STDMETHODCALLTYPE CFastFileOpDeleteCommand::GetTitle(
    IShellItemArray* psiItemArray,
    LPWSTR* ppszName)
{
    if (!ppszName)
        return E_POINTER;

    // 检查 Python 服务是否在线
    if (!PipeClient::IsServiceOnline())
    {
        *ppszName = nullptr;
        return E_FAIL;
    }

    // 检查是否有选中文件
    DWORD count = 0;
    if (psiItemArray)
    {
        psiItemArray->GetCount(&count);
    }

    if (count == 0)
    {
        *ppszName = nullptr;
        return E_FAIL;
    }

    // 返回菜单标题
    return SHStrDupW(L"删除 (FastFileOp)", ppszName);
}

HRESULT STDMETHODCALLTYPE CFastFileOpDeleteCommand::GetIcon(
    IShellItemArray* psiItemArray,
    LPWSTR* ppszIcon)
{
    if (!ppszIcon)
        return E_POINTER;

    // 使用系统删除图标
    return SHStrDupW(L"shell32.dll,-240", ppszIcon);
}

HRESULT STDMETHODCALLTYPE CFastFileOpDeleteCommand::GetToolTip(
    IShellItemArray* psiItemArray,
    LPWSTR* ppszInfotip)
{
    if (!ppszInfotip)
        return E_POINTER;

    return SHStrDupW(L"使用 FastFileOp 高速删除", ppszInfotip);
}

HRESULT STDMETHODCALLTYPE CFastFileOpDeleteCommand::GetCanonicalName(
    GUID* pguidCommandName)
{
    if (!pguidCommandName)
        return E_POINTER;

    *pguidCommandName = CLSID_FastFileOpDeleteCommand;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE CFastFileOpDeleteCommand::GetState(
    IShellItemArray* psiItemArray,
    BOOL fOkToBeSlow,
    EXPCMDSTATE* pCmdState)
{
    if (!pCmdState)
        return E_POINTER;

    // 检查 Python 服务是否在线
    if (!PipeClient::IsServiceOnline())
    {
        *pCmdState = ECS_HIDDEN;
        return S_OK;
    }

    // 检查是否有选中文件
    DWORD count = 0;
    if (psiItemArray)
    {
        psiItemArray->GetCount(&count);
    }

    *pCmdState = (count > 0) ? ECS_ENABLED : ECS_HIDDEN;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE CFastFileOpDeleteCommand::Invoke(
    IShellItemArray* psiItemArray,
    IBindCtx* pbc)
{
    // 获取选中的文件
    std::vector<std::wstring> files;
    if (!GetSelectedFiles(psiItemArray, files) || files.empty())
        return S_OK;

    // 检查 Shift 键状态
    bool permanent = (GetKeyState(VK_SHIFT) & 0x8000) != 0;

    // 发送到 Python
    SendToPython(files, permanent);

    return S_OK;
}

HRESULT STDMETHODCALLTYPE CFastFileOpDeleteCommand::GetFlags(
    EXPCMDFLAGS* pFlags)
{
    if (!pFlags)
        return E_POINTER;

    *pFlags = ECF_DEFAULT;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE CFastFileOpDeleteCommand::EnumSubCommands(
    IEnumExplorerCommand** ppEnum)
{
    if (!ppEnum)
        return E_POINTER;

    *ppEnum = nullptr;
    return E_NOTIMPL;
}

bool CFastFileOpDeleteCommand::GetSelectedFiles(
    IShellItemArray* psiItemArray,
    std::vector<std::wstring>& files)
{
    files.clear();

    if (!psiItemArray)
        return false;

    DWORD count = 0;
    if (FAILED(psiItemArray->GetCount(&count)) || count == 0)
        return false;

    for (DWORD i = 0; i < count; ++i)
    {
        CComPtr<IShellItem> pItem;
        if (FAILED(psiItemArray->GetItemAt(i, &pItem)))
            continue;

        LPWSTR pszPath = nullptr;
        if (SUCCEEDED(pItem->GetDisplayName(SIGDN_FILESYSPATH, &pszPath)))
        {
            files.push_back(pszPath);
            CoTaskMemFree(pszPath);
        }
    }

    return !files.empty();
}

bool CFastFileOpDeleteCommand::SendToPython(
    const std::vector<std::wstring>& files,
    bool permanent)
{
    std::wstring action = permanent ? L"delete_permanent" : L"delete";
    std::wstring request = Utils::BuildJsonMessage(action, files, L"");
    std::wstring response;

    if (PipeClient::SendRequest(request, response, PIPE_OPERATION_TIMEOUT_DELETE))
    {
        bool success = false;
        std::vector<std::wstring> failed;
        return Utils::ParseJsonResponse(response, success, failed) && success;
    }

    return false;
}
