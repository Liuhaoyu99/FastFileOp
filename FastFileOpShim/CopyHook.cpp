// CopyHook.cpp : ICopyHook implementation

#include "stdafx.h"
#include "CopyHook.h"
#include "PipeClient.h"

UINT STDMETHODCALLTYPE CFastFileOpCopyHook::CopyCallback(
    HWND hwnd,
    UINT wFunc,
    UINT wFlags,
    LPCWSTR pszSrcFile,
    DWORD dwSrcAttribs,
    LPCWSTR pszDestFile,
    DWORD dwDestAttribs)
{
    // Only handle folder operations
    if (!(dwSrcAttribs & FILE_ATTRIBUTE_DIRECTORY))
    {
        return IDYES;
    }

    std::wstring action;
    switch (wFunc)
    {
    case FO_COPY:
        action = L"copy";
        break;
    case FO_MOVE:
        action = L"move";
        break;
    case FO_DELETE:
        action = L"delete";
        break;
    default:
        return IDYES;
    }

    if (!PipeClient::IsServiceOnline())
    {
        return IDYES;
    }

    std::wstring src = pszSrcFile ? pszSrcFile : L"";
    std::wstring dst = pszDestFile ? pszDestFile : L"";

    if (SendToPython(action, src, dst))
    {
        return IDNO;
    }
    else
    {
        return IDYES;
    }
}

bool CFastFileOpCopyHook::SendToPython(
    const std::wstring& action,
    const std::wstring& src,
    const std::wstring& dst)
{
    std::vector<std::wstring> srcList;
    srcList.push_back(src);

    std::wstring request = Utils::BuildJsonMessage(action, srcList, dst);
    std::wstring response;

    DWORD timeout = (action == L"delete") ?
        PIPE_OPERATION_TIMEOUT_DELETE : PIPE_OPERATION_TIMEOUT_COPY;

    if (PipeClient::SendRequest(request, response, timeout))
    {
        bool success = false;
        std::vector<std::wstring> failed;
        if (Utils::ParseJsonResponse(response, success, failed))
        {
            return success;
        }
    }

    return false;
}
