// dllmain.cpp : DLL entry point and exports

#include "stdafx.h"
#include "CopyHook.h"
#include "DropTarget.h"
#include "ContextMenu.h"
#include "ExplorerCommand.h"

HINSTANCE g_hInst = NULL;
DWORD g_dwRegister = 0;

// Class Factory for DropTarget
class CDropTargetClassFactory : public IClassFactory, public RefCount
{
public:
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override
    {
        if (riid == IID_IUnknown || riid == IID_IClassFactory)
        {
            *ppv = static_cast<IClassFactory*>(this);
            AddRef();
            return S_OK;
        }
        *ppv = NULL;
        return E_NOINTERFACE;
    }

    STDMETHODIMP_(ULONG) AddRef() override { return RefCount::AddRef(); }
    STDMETHODIMP_(ULONG) Release() override { return RefCount::Release(); }

    STDMETHODIMP CreateInstance(IUnknown* pUnkOuter, REFIID riid, void** ppv) override
    {
        if (pUnkOuter) return CLASS_E_NOAGGREGATION;

        CFastFileOpDropTarget* pObj = new CFastFileOpDropTarget();
        if (!pObj) return E_OUTOFMEMORY;

        HRESULT hr = pObj->QueryInterface(riid, ppv);
        pObj->Release();
        return hr;
    }

    STDMETHODIMP LockServer(BOOL fLock) override { return S_OK; }
};

// Helper: format CLSID as "{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"
static void FormatCLSID(const CLSID& clsid, WCHAR* buf, size_t bufLen)
{
    swprintf_s(buf, bufLen,
        L"{%08lX-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X}",
        clsid.Data1, clsid.Data2, clsid.Data3,
        clsid.Data4[0], clsid.Data4[1], clsid.Data4[2], clsid.Data4[3],
        clsid.Data4[4], clsid.Data4[5], clsid.Data4[6], clsid.Data4[7]);
}

// Helper: register a CLSID's InprocServer32 and description
static void RegisterCLSID(const CLSID& clsid, LPCWSTR description, LPCWSTR modulePath)
{
    WCHAR szKey[MAX_PATH * 2];
    WCHAR szCLSID[64];
    HKEY hKey;

    FormatCLSID(clsid, szCLSID, 64);

    // CLSID\{clsid}
    swprintf_s(szKey, MAX_PATH * 2, L"CLSID\\%s", szCLSID);
    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, szKey, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL) == ERROR_SUCCESS)
    {
        RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)description,
            (DWORD)((wcslen(description) + 1) * sizeof(WCHAR)));
        RegCloseKey(hKey);
    }

    // CLSID\{clsid}\InprocServer32
    wcscat_s(szKey, L"\\InprocServer32");
    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, szKey, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL) == ERROR_SUCCESS)
    {
        RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)modulePath,
            (DWORD)((wcslen(modulePath) + 1) * sizeof(WCHAR)));
        RegSetValueExW(hKey, L"ThreadingModel", 0, REG_SZ,
            (const BYTE*)L"Apartment", sizeof(L"Apartment"));
        RegCloseKey(hKey);
    }
}

// Helper: unregister a CLSID and all subkeys
static void UnregisterCLSID(const CLSID& clsid)
{
    WCHAR szKey[MAX_PATH * 2];
    WCHAR szCLSID[64];

    FormatCLSID(clsid, szCLSID, 64);

    // Delete InprocServer32 first
    swprintf_s(szKey, MAX_PATH * 2, L"CLSID\\%s\\InprocServer32", szCLSID);
    RegDeleteKeyW(HKEY_CLASSES_ROOT, szKey);

    // Delete CLSID root
    swprintf_s(szKey, MAX_PATH * 2, L"CLSID\\%s", szCLSID);
    RegDeleteKeyW(HKEY_CLASSES_ROOT, szKey);
}

// Helper: register a handler under ShellEx (CopyHookHandlers, DragDropHandlers, etc.)
static void RegisterShellExHandler(const CLSID& clsid, LPCWSTR handlerPath, LPCWSTR handlerName)
{
    WCHAR szCLSID[64];
    WCHAR szFullKey[MAX_PATH * 2];
    HKEY hKey;

    FormatCLSID(clsid, szCLSID, 64);

    swprintf_s(szFullKey, MAX_PATH * 2, L"%s\\%s", handlerPath, handlerName);
    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, szFullKey, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL) == ERROR_SUCCESS)
    {
        RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)szCLSID,
            (DWORD)((wcslen(szCLSID) + 1) * sizeof(WCHAR)));
        RegCloseKey(hKey);
    }
}

// Helper: unregister a handler from ShellEx
static void UnregisterShellExHandler(LPCWSTR handlerPath, LPCWSTR handlerName)
{
    WCHAR szFullKey[MAX_PATH * 2];
    swprintf_s(szFullKey, MAX_PATH * 2, L"%s\\%s", handlerPath, handlerName);
    RegDeleteKeyW(HKEY_CLASSES_ROOT, szFullKey);
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        DisableThreadLibraryCalls(hModule);
        g_hInst = hModule;
        break;
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}

STDAPI DllGetClassObject(REFCLSID rclsid, REFIID riid, LPVOID* ppv)
{
    if (rclsid == CLSID_FastFileOpCopyHook)
    {
        CCopyHookClassFactory* pFactory = new CCopyHookClassFactory();
        if (!pFactory) return E_OUTOFMEMORY;

        HRESULT hr = pFactory->QueryInterface(riid, ppv);
        pFactory->Release();
        return hr;
    }

    if (rclsid == CLSID_FastFileOpDropTarget)
    {
        CDropTargetClassFactory* pFactory = new CDropTargetClassFactory();
        if (!pFactory) return E_OUTOFMEMORY;

        HRESULT hr = pFactory->QueryInterface(riid, ppv);
        pFactory->Release();
        return hr;
    }

    if (rclsid == CLSID_FastFileOpContextMenu)
    {
        CComObject<CFastFileOpContextMenu>* pObject = NULL;
        HRESULT hr = CComObject<CFastFileOpContextMenu>::CreateInstance(&pObject);
        if (FAILED(hr) || !pObject) return E_OUTOFMEMORY;

        hr = pObject->QueryInterface(riid, ppv);
        pObject->Release();
        return hr;
    }

    if (rclsid == CLSID_FastFileOpDeleteCommand)
    {
        CComObject<CFastFileOpDeleteCommand>* pObject = NULL;
        HRESULT hr = CComObject<CFastFileOpDeleteCommand>::CreateInstance(&pObject);
        if (FAILED(hr) || !pObject) return E_OUTOFMEMORY;

        hr = pObject->QueryInterface(riid, ppv);
        pObject->Release();
        return hr;
    }

    return CLASS_E_CLASSNOTAVAILABLE;
}

STDAPI DllCanUnloadNow()
{
    return S_OK;
}

STDAPI DllRegisterServer()
{
    WCHAR szModulePath[MAX_PATH];
    GetModuleFileNameW(g_hInst, szModulePath, MAX_PATH);

    // ── CopyHook ───────────────────────────────────────────────
    RegisterCLSID(CLSID_FastFileOpCopyHook, L"FastFileOp CopyHook", szModulePath);
    RegisterShellExHandler(CLSID_FastFileOpCopyHook,
        L"Directory\\ShellEx\\CopyHookHandlers", L"FastFileOp");
    RegisterShellExHandler(CLSID_FastFileOpCopyHook,
        L"Folder\\ShellEx\\CopyHookHandlers", L"FastFileOp");

    // ── DropTarget (DragDropHandler) ───────────────────────────
    RegisterCLSID(CLSID_FastFileOpDropTarget, L"FastFileOp DropTarget", szModulePath);
    RegisterShellExHandler(CLSID_FastFileOpDropTarget,
        L"Directory\\ShellEx\\DragDropHandlers", L"FastFileOp");
    RegisterShellExHandler(CLSID_FastFileOpDropTarget,
        L"Folder\\ShellEx\\DragDropHandlers", L"FastFileOp");

    // ── ContextMenu ────────────────────────────────────────────
    RegisterCLSID(CLSID_FastFileOpContextMenu, L"FastFileOp ContextMenu", szModulePath);
    RegisterShellExHandler(CLSID_FastFileOpContextMenu,
        L"*\\ShellEx\\ContextMenuHandlers", L"FastFileOp");
    RegisterShellExHandler(CLSID_FastFileOpContextMenu,
        L"Directory\\ShellEx\\ContextMenuHandlers", L"FastFileOp");
    RegisterShellExHandler(CLSID_FastFileOpContextMenu,
        L"Folder\\ShellEx\\ContextMenuHandlers", L"FastFileOp");

    // ── DeleteCommand ──────────────────────────────────────────
    RegisterCLSID(CLSID_FastFileOpDeleteCommand, L"FastFileOp DeleteCommand", szModulePath);
    RegisterShellExHandler(CLSID_FastFileOpDeleteCommand,
        L"*\\ShellEx\\ContextMenuHandlers", L"FastFileOpDelete");
    RegisterShellExHandler(CLSID_FastFileOpDeleteCommand,
        L"Directory\\ShellEx\\ContextMenuHandlers", L"FastFileOpDelete");

    // Notify Shell
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);

    return S_OK;
}

STDAPI DllUnregisterServer()
{
    // ── CopyHook ───────────────────────────────────────────────
    UnregisterShellExHandler(L"Directory\\ShellEx\\CopyHookHandlers", L"FastFileOp");
    UnregisterShellExHandler(L"Folder\\ShellEx\\CopyHookHandlers", L"FastFileOp");
    UnregisterCLSID(CLSID_FastFileOpCopyHook);

    // ── DropTarget ─────────────────────────────────────────────
    UnregisterShellExHandler(L"Directory\\ShellEx\\DragDropHandlers", L"FastFileOp");
    UnregisterShellExHandler(L"Folder\\ShellEx\\DragDropHandlers", L"FastFileOp");
    UnregisterCLSID(CLSID_FastFileOpDropTarget);

    // ── ContextMenu ────────────────────────────────────────────
    UnregisterShellExHandler(L"*\\ShellEx\\ContextMenuHandlers", L"FastFileOp");
    UnregisterShellExHandler(L"Directory\\ShellEx\\ContextMenuHandlers", L"FastFileOp");
    UnregisterShellExHandler(L"Folder\\ShellEx\\ContextMenuHandlers", L"FastFileOp");
    UnregisterCLSID(CLSID_FastFileOpContextMenu);

    // ── DeleteCommand ──────────────────────────────────────────
    UnregisterShellExHandler(L"*\\ShellEx\\ContextMenuHandlers", L"FastFileOpDelete");
    UnregisterShellExHandler(L"Directory\\ShellEx\\ContextMenuHandlers", L"FastFileOpDelete");
    UnregisterCLSID(CLSID_FastFileOpDeleteCommand);

    // Notify Shell
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);

    return S_OK;
}
