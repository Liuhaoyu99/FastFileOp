// ExplorerCommand.h : IExplorerCommand 接口实现
//

#pragma once

#include "stdafx.h"

// IExplorerCommand 实现 - 右键菜单「FastFileOp 删除」
class ATL_NO_VTABLE CFastFileOpDeleteCommand :
    public CComObjectRootEx<CComSingleThreadModel>,
    public CComCoClass<CFastFileOpDeleteCommand, &CLSID_FastFileOpDeleteCommand>,
    public IExplorerCommand
{
public:
    CFastFileOpDeleteCommand() = default;
    virtual ~CFastFileOpDeleteCommand() = default;

    DECLARE_REGISTRY_RESOURCEID(104)  // DeleteCommand.rgs

    BEGIN_COM_MAP(CFastFileOpDeleteCommand)
        COM_INTERFACE_ENTRY(IExplorerCommand)
    END_COM_MAP()

    // IExplorerCommand
    HRESULT STDMETHODCALLTYPE GetTitle(
        IShellItemArray* psiItemArray,
        LPWSTR* ppszName) override;

    HRESULT STDMETHODCALLTYPE GetIcon(
        IShellItemArray* psiItemArray,
        LPWSTR* ppszIcon) override;

    HRESULT STDMETHODCALLTYPE GetToolTip(
        IShellItemArray* psiItemArray,
        LPWSTR* ppszInfotip) override;

    HRESULT STDMETHODCALLTYPE GetCanonicalName(
        GUID* pguidCommandName) override;

    HRESULT STDMETHODCALLTYPE GetState(
        IShellItemArray* psiItemArray,
        BOOL fOkToBeSlow,
        EXPCMDSTATE* pCmdState) override;

    HRESULT STDMETHODCALLTYPE Invoke(
        IShellItemArray* psiItemArray,
        IBindCtx* pbc) override;

    HRESULT STDMETHODCALLTYPE GetFlags(
        EXPCMDFLAGS* pFlags) override;

    HRESULT STDMETHODCALLTYPE EnumSubCommands(
        IEnumExplorerCommand** ppEnum) override;

    DECLARE_PROTECT_FINAL_CONSTRUCT()

private:
    bool GetSelectedFiles(IShellItemArray* psiItemArray, std::vector<std::wstring>& files);
    bool SendToPython(const std::vector<std::wstring>& files, bool permanent);
};

OBJECT_ENTRY_AUTO(__uuidof(FastFileOpDeleteCommand), CFastFileOpDeleteCommand)
