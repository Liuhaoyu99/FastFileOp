// dllmain.cpp : DLL entry point and exports

#include "stdafx.h"
#include "CopyHook.h"

HINSTANCE g_hInst = NULL;
DWORD g_dwRegister = 0;

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

    // Register CopyHook
    WCHAR szKey[MAX_PATH * 2];

    // HKCR\CLSID\{CLSID}
    swprintf_s(szKey, L"CLSID\\%08lX-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X",
        CLSID_FastFileOpCopyHook.Data1, CLSID_FastFileOpCopyHook.Data2,
        CLSID_FastFileOpCopyHook.Data3, CLSID_FastFileOpCopyHook.Data4[0],
        CLSID_FastFileOpCopyHook.Data4[1], CLSID_FastFileOpCopyHook.Data4[2],
        CLSID_FastFileOpCopyHook.Data4[3], CLSID_FastFileOpCopyHook.Data4[4],
        CLSID_FastFileOpCopyHook.Data4[5], CLSID_FastFileOpCopyHook.Data4[6],
        CLSID_FastFileOpCopyHook.Data4[7]);

    HKEY hKey;
    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, szKey, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL) == ERROR_SUCCESS)
    {
        RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)L"FastFileOp CopyHook", sizeof(L"FastFileOp CopyHook"));
        RegCloseKey(hKey);
    }

    // InprocServer32
    wcscat_s(szKey, L"\\InprocServer32");
    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, szKey, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL) == ERROR_SUCCESS)
    {
        RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)szModulePath, (DWORD)(wcslen(szModulePath) + 1) * sizeof(WCHAR));
        RegSetValueExW(hKey, L"ThreadingModel", 0, REG_SZ, (const BYTE*)L"Apartment", sizeof(L"Apartment"));
        RegCloseKey(hKey);
    }

    // Register under CopyHookHandlers
    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, L"Directory\\ShellEx\\CopyHookHandlers\\FastFileOp", 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL) == ERROR_SUCCESS)
    {
        WCHAR szCLSID[64];
        swprintf_s(szCLSID, L"{%08lX-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X}",
            CLSID_FastFileOpCopyHook.Data1, CLSID_FastFileOpCopyHook.Data2,
            CLSID_FastFileOpCopyHook.Data3, CLSID_FastFileOpCopyHook.Data4[0],
            CLSID_FastFileOpCopyHook.Data4[1], CLSID_FastFileOpCopyHook.Data4[2],
            CLSID_FastFileOpCopyHook.Data4[3], CLSID_FastFileOpCopyHook.Data4[4],
            CLSID_FastFileOpCopyHook.Data4[5], CLSID_FastFileOpCopyHook.Data4[6],
            CLSID_FastFileOpCopyHook.Data4[7]);
        RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)szCLSID, (DWORD)(wcslen(szCLSID) + 1) * sizeof(WCHAR));
        RegCloseKey(hKey);
    }

    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, L"Folder\\ShellEx\\CopyHookHandlers\\FastFileOp", 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL) == ERROR_SUCCESS)
    {
        WCHAR szCLSID[64];
        swprintf_s(szCLSID, L"{%08lX-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X}",
            CLSID_FastFileOpCopyHook.Data1, CLSID_FastFileOpCopyHook.Data2,
            CLSID_FastFileOpCopyHook.Data3, CLSID_FastFileOpCopyHook.Data4[0],
            CLSID_FastFileOpCopyHook.Data4[1], CLSID_FastFileOpCopyHook.Data4[2],
            CLSID_FastFileOpCopyHook.Data4[3], CLSID_FastFileOpCopyHook.Data4[4],
            CLSID_FastFileOpCopyHook.Data4[5], CLSID_FastFileOpCopyHook.Data4[6],
            CLSID_FastFileOpCopyHook.Data4[7]);
        RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)szCLSID, (DWORD)(wcslen(szCLSID) + 1) * sizeof(WCHAR));
        RegCloseKey(hKey);
    }

    // Notify Shell
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);

    return S_OK;
}

STDAPI DllUnregisterServer()
{
    WCHAR szKey[MAX_PATH * 2];

    // Remove CopyHookHandlers entries
    RegDeleteKeyW(HKEY_CLASSES_ROOT, L"Directory\\ShellEx\\CopyHookHandlers\\FastFileOp");
    RegDeleteKeyW(HKEY_CLASSES_ROOT, L"Folder\\ShellEx\\CopyHookHandlers\\FastFileOp");

    // Remove CLSID entries
    swprintf_s(szKey, L"CLSID\\%08lX-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X\\InprocServer32",
        CLSID_FastFileOpCopyHook.Data1, CLSID_FastFileOpCopyHook.Data2,
        CLSID_FastFileOpCopyHook.Data3, CLSID_FastFileOpCopyHook.Data4[0],
        CLSID_FastFileOpCopyHook.Data4[1], CLSID_FastFileOpCopyHook.Data4[2],
        CLSID_FastFileOpCopyHook.Data4[3], CLSID_FastFileOpCopyHook.Data4[4],
        CLSID_FastFileOpCopyHook.Data4[5], CLSID_FastFileOpCopyHook.Data4[6],
        CLSID_FastFileOpCopyHook.Data4[7]);
    RegDeleteKeyW(HKEY_CLASSES_ROOT, szKey);

    swprintf_s(szKey, L"CLSID\\%08lX-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X",
        CLSID_FastFileOpCopyHook.Data1, CLSID_FastFileOpCopyHook.Data2,
        CLSID_FastFileOpCopyHook.Data3, CLSID_FastFileOpCopyHook.Data4[0],
        CLSID_FastFileOpCopyHook.Data4[1], CLSID_FastFileOpCopyHook.Data4[2],
        CLSID_FastFileOpCopyHook.Data4[3], CLSID_FastFileOpCopyHook.Data4[4],
        CLSID_FastFileOpCopyHook.Data4[5], CLSID_FastFileOpCopyHook.Data4[6],
        CLSID_FastFileOpCopyHook.Data4[7]);
    RegDeleteKeyW(HKEY_CLASSES_ROOT, szKey);

    // Notify Shell
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);

    return S_OK;
}
