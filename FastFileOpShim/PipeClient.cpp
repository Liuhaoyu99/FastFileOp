// PipeClient.cpp : Named Pipe client implementation

#include "stdafx.h"
#include "PipeClient.h"

namespace PipeClient
{
    bool SendRequest(
        const std::wstring& request,
        std::wstring& response,
        DWORD timeoutMs)
    {
        HANDLE hPipe = INVALID_HANDLE_VALUE;
        BOOL bSuccess = FALSE;
        DWORD dwMode;
        DWORD dwRead = 0, dwWritten = 0;

        hPipe = CreateFileW(
            FASTFILEOP_PIPE_NAME,
            GENERIC_READ | GENERIC_WRITE,
            0,
            NULL,
            OPEN_EXISTING,
            FILE_FLAG_OVERLAPPED,
            NULL
        );

        if (hPipe == INVALID_HANDLE_VALUE)
        {
            return false;
        }

        dwMode = PIPE_READMODE_MESSAGE;
        bSuccess = SetNamedPipeHandleState(
            hPipe,
            &dwMode,
            NULL,
            NULL
        );

        if (!bSuccess)
        {
            CloseHandle(hPipe);
            return false;
        }

        HANDLE hEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
        if (hEvent == NULL)
        {
            CloseHandle(hPipe);
            return false;
        }

        OVERLAPPED overlapped = { 0 };
        overlapped.hEvent = hEvent;

        std::string requestUtf8;
        int len = WideCharToMultiByte(CP_UTF8, 0, request.c_str(), -1, NULL, 0, NULL, NULL);
        if (len > 0)
        {
            requestUtf8.resize(len - 1);
            WideCharToMultiByte(CP_UTF8, 0, request.c_str(), -1, &requestUtf8[0], len, NULL, NULL);
        }

        requestUtf8 += "\n";

        bSuccess = WriteFile(
            hPipe,
            requestUtf8.data(),
            static_cast<DWORD>(requestUtf8.size()),
            &dwWritten,
            &overlapped
        );

        if (!bSuccess && GetLastError() != ERROR_IO_PENDING)
        {
            CloseHandle(hEvent);
            CloseHandle(hPipe);
            return false;
        }

        if (!bSuccess)
        {
            DWORD waitResult = WaitForSingleObject(hEvent, timeoutMs);
            if (waitResult != WAIT_OBJECT_0)
            {
                CancelIo(hPipe);
                CloseHandle(hEvent);
                CloseHandle(hPipe);
                return false;
            }
            GetOverlappedResult(hPipe, &overlapped, &dwWritten, FALSE);
        }

        ResetEvent(hEvent);

        char buffer[4096];
        std::string responseUtf8;

        while (true)
        {
            bSuccess = ReadFile(
                hPipe,
                buffer,
                sizeof(buffer) - 1,
                &dwRead,
                &overlapped
            );

            if (!bSuccess && GetLastError() != ERROR_IO_PENDING)
            {
                if (GetLastError() == ERROR_BROKEN_PIPE)
                {
                    break;
                }
                CloseHandle(hEvent);
                CloseHandle(hPipe);
                return false;
            }

            if (!bSuccess)
            {
                DWORD waitResult = WaitForSingleObject(hEvent, timeoutMs);
                if (waitResult != WAIT_OBJECT_0)
                {
                    CancelIo(hPipe);
                    CloseHandle(hEvent);
                    CloseHandle(hPipe);
                    return false;
                }
                GetOverlappedResult(hPipe, &overlapped, &dwRead, FALSE);
            }

            if (dwRead == 0)
                break;

            buffer[dwRead] = '\0';
            responseUtf8 += buffer;

            if (!responseUtf8.empty() && responseUtf8.back() == '\n')
            {
                responseUtf8.pop_back();
                break;
            }
        }

        CloseHandle(hEvent);
        CloseHandle(hPipe);

        if (!responseUtf8.empty())
        {
            int wlen = MultiByteToWideChar(CP_UTF8, 0, responseUtf8.c_str(), -1, NULL, 0);
            if (wlen > 0)
            {
                response.resize(wlen - 1);
                MultiByteToWideChar(CP_UTF8, 0, responseUtf8.c_str(), -1, &response[0], wlen);
            }
            return true;
        }

        return false;
    }

    bool IsServiceOnline()
    {
        HANDLE hPipe = CreateFileW(
            FASTFILEOP_PIPE_NAME,
            GENERIC_READ | GENERIC_WRITE,
            0,
            NULL,
            OPEN_EXISTING,
            0,
            NULL
        );

        if (hPipe == INVALID_HANDLE_VALUE)
        {
            return false;
        }

        CloseHandle(hPipe);
        return true;
    }
}
