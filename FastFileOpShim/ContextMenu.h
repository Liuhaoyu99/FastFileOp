// ContextMenu.h : IContextMenu 接口实现
//

#pragma once

#include "stdafx.h"

// IContextMenu 实现 - 右键菜单「粘贴」拦截
class ATL_NO_VTABLE CFastFileOpContextMenu :
    public CComObjectRootEx<CComSingleThreadModel>,
    public CComCoClass<CFastFileOpContextMenu, &CLSID_FastFileOpContextMenu>,
    public IShellExtInit,
    public IContextMenu
{
public:
    CFastFileOpContextMenu() = default;
    virtual ~CFastFileOpContextMenu() = default;

    DECLARE_REGISTRY_RESOURCEID(102)  // ContextMenu.rgs

    BEGIN_COM_MAP(CFastFileOpContextMenu)
        COM_INTERFACE_ENTRY(IShellExtInit)
        COM_INTERFACE_ENTRY(IContextMenu)
    END_COM_MAP()

    // IShellExtInit
    HRESULT STDMETHODCALLTYPE Initialize(
        LPCITEMIDLIST pidlFolder,
        LPDATAOBJECT pDataObj,
        HKEY hkeyProgID) override;

    // IContextMenu
    HRESULT STDMETHODCALLTYPE QueryContextMenu(
        HMENU hmenu,
        UINT indexMenu,
        UINT idCmdFirst,
        UINT idCmdLast,
        UINT uFlags) override;

    HRESULT STDMETHODCALLTYPE InvokeCommand(
        CMINVOKECOMMANDINFO* pici) override;

    HRESULT STDMETHODCALLTYPE GetCommandString(
        UINT_PTR idCmd,
        UINT uFlags,
        UINT* pwReserved,
        LPSTR pszName,
        UINT cchMax) override;

    DECLARE_PROTECT_FINAL_CONSTRUCT()

private:
    std::wstring m_targetFolder;
    std::vector<std::wstring> m_selectedFiles;

    bool GetClipboardFiles(std::vector<std::wstring>& files);
    bool SendToPython(const std::wstring& action, const std::vector<std::wstring>& src, const std::wstring& dst);
};

OBJECT_ENTRY_AUTO(__uuidof(FastFileOpContextMenu), CFastFileOpContextMenu)
