// DropTarget.h : IDropTarget 接口实现
//

#pragma once

#include "stdafx.h"

// IDropTarget 实现 - 拦截拖拽操作
class ATL_NO_VTABLE CFastFileOpDropTarget :
    public CComObjectRootEx<CComSingleThreadModel>,
    public CComCoClass<CFastFileOpDropTarget, &CLSID_FastFileOpDropTarget>,
    public IDropTarget
{
public:
    CFastFileOpDropTarget() = default;
    virtual ~CFastFileOpDropTarget() = default;

    DECLARE_REGISTRY_RESOURCEID(103)  // DropTarget.rgs

    BEGIN_COM_MAP(CFastFileOpDropTarget)
        COM_INTERFACE_ENTRY(IDropTarget)
    END_COM_MAP()

    // IDropTarget
    HRESULT STDMETHODCALLTYPE DragEnter(
        IDataObject* pDataObj,
        DWORD grfKeyState,
        POINTL pt,
        DWORD* pdwEffect) override;

    HRESULT STDMETHODCALLTYPE DragOver(
        DWORD grfKeyState,
        POINTL pt,
        DWORD* pdwEffect) override;

    HRESULT STDMETHODCALLTYPE DragLeave() override;

    HRESULT STDMETHODCALLTYPE Drop(
        IDataObject* pDataObj,
        DWORD grfKeyState,
        POINTL pt,
        DWORD* pdwEffect) override;

    DECLARE_PROTECT_FINAL_CONSTRUCT()

private:
    bool m_canDrop = false;
    DWORD m_dropEffect = DROPEFFECT_NONE;

    bool GetDropFiles(IDataObject* pDataObj, std::vector<std::wstring>& files);
    bool SendToPython(const std::wstring& action, const std::vector<std::wstring>& src, const std::wstring& dst);
};

OBJECT_ENTRY_AUTO(__uuidof(FastFileOpDropTarget), CFastFileOpDropTarget)
