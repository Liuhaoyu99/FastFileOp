// PipeClient.h : Named Pipe client communication

#pragma once

#include "stdafx.h"

namespace PipeClient
{
    bool SendRequest(
        const std::wstring& request,
        std::wstring& response,
        DWORD timeoutMs
    );

    bool IsServiceOnline();
}
