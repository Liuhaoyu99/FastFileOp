// stdafx.h : Precompiled header file
// Pure Win32 API - No ATL dependency

#pragma once

#ifndef STRICT
#define STRICT
#endif

#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#define WINVER 0x0601

#include <windows.h>
#include <shlobj.h>
#include <shobjidl.h>
#include <shellapi.h>
#include <comdef.h>
#include <string>
#include <vector>
#include <memory>

// Pipe name
#define FASTFILEOP_PIPE_NAME L"\\\\.\\pipe\\FastFileOpPipe"

// Timeouts (milliseconds)
#define PIPE_CONNECT_TIMEOUT 2000
#define PIPE_OPERATION_TIMEOUT_COPY 60000
#define PIPE_OPERATION_TIMEOUT_DELETE 30000

// CLSIDs
// {A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
static const CLSID CLSID_FastFileOpCopyHook =
{ 0xa1b2c3d4, 0xe5f6, 0x7890, { 0xab, 0xcd, 0xef, 0x12, 0x34, 0x56, 0x78, 0x90 } };

// {B2C3D4E5-F6A7-8901-BCDE-F12345678901}
static const CLSID CLSID_FastFileOpContextMenu =
{ 0xb2c3d4e5, 0xf6a7, 0x8901, { 0xbc, 0xde, 0xf1, 0x23, 0x45, 0x67, 0x89, 0x01 } };

// {C3D4E5F6-A7B8-9012-CDEF-123456789012}
static const CLSID CLSID_FastFileOpDropTarget =
{ 0xc3d4e5f6, 0xa7b8, 0x9012, { 0xcd, 0xef, 0x12, 0x34, 0x56, 0x78, 0x90, 0x12 } };

// {D4E5F6A7-B8C9-0123-DEF0-234567890123}
static const CLSID CLSID_FastFileOpDeleteCommand =
{ 0xd4e5f6a7, 0xb8c9, 0x0123, { 0xde, 0xf0, 0x23, 0x45, 0x67, 0x89, 0x01, 0x23 } };

// Helper functions
namespace Utils
{
    std::wstring EscapeJsonString(const std::wstring& input);
    std::wstring BuildJsonMessage(const std::wstring& action,
                                   const std::vector<std::wstring>& src,
                                   const std::wstring& dst);
    bool ParseJsonResponse(const std::wstring& json,
                           bool& success,
                           std::vector<std::wstring>& failed);
}

// Reference count helper
class RefCount
{
public:
    RefCount() : m_ref(1) {}
    virtual ~RefCount() {}

    ULONG AddRef() { return InterlockedIncrement(&m_ref); }
    ULONG Release()
    {
        LONG ref = InterlockedDecrement(&m_ref);
        if (ref == 0) delete this;
        return ref;
    }

private:
    LONG m_ref;
};
