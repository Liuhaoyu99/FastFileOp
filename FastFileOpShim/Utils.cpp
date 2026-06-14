// Utils.cpp : Utility functions

#include "stdafx.h"
#include <sstream>

namespace Utils
{
    std::wstring EscapeJsonString(const std::wstring& input)
    {
        std::wstring output;
        output.reserve(input.size() * 2);

        for (wchar_t c : input)
        {
            switch (c)
            {
            case L'"':
                output += L"\\\"";
                break;
            case L'\\':
                output += L"\\\\";
                break;
            case L'\b':
                output += L"\\b";
                break;
            case L'\f':
                output += L"\\f";
                break;
            case L'\n':
                output += L"\\n";
                break;
            case L'\r':
                output += L"\\r";
                break;
            case L'\t':
                output += L"\\t";
                break;
            default:
                if (c < 0x20)
                {
                    wchar_t buf[16];
                    swprintf_s(buf, L"\\u%04x", (int)c);
                    output += buf;
                }
                else
                {
                    output += c;
                }
            }
        }
        return output;
    }

    std::wstring BuildJsonMessage(
        const std::wstring& action,
        const std::vector<std::wstring>& src,
        const std::wstring& dst)
    {
        std::wostringstream oss;
        oss << L"{\"action\":\"" << action << L"\",\"src\":[";

        for (size_t i = 0; i < src.size(); ++i)
        {
            if (i > 0) oss << L",";
            oss << L"\"" << EscapeJsonString(src[i]) << L"\"";
        }

        oss << L"],\"dst\":\"" << EscapeJsonString(dst) << L"\"}";
        return oss.str();
    }

    bool ParseJsonResponse(
        const std::wstring& json,
        bool& success,
        std::vector<std::wstring>& failed)
    {
        success = false;
        failed.clear();

        size_t statusPos = json.find(L"\"status\"");
        if (statusPos == std::wstring::npos)
            return false;

        size_t colonPos = json.find(L':', statusPos);
        if (colonPos == std::wstring::npos)
            return false;

        size_t valueStart = json.find_first_not_of(L" \t\n\r", colonPos + 1);
        if (valueStart == std::wstring::npos)
            return false;

        if (json.substr(valueStart, 4) == L"\"ok\"")
        {
            success = true;
        }
        else if (json.substr(valueStart, 7) == L"\"error\"")
        {
            success = false;
        }
        else
        {
            return false;
        }

        size_t failedPos = json.find(L"\"failed\"");
        if (failedPos == std::wstring::npos)
            return true;

        size_t arrayStart = json.find(L'[', failedPos);
        if (arrayStart == std::wstring::npos)
            return true;

        size_t arrayEnd = json.find(L']', arrayStart);
        if (arrayEnd == std::wstring::npos)
            return true;

        std::wstring arrayContent = json.substr(arrayStart + 1, arrayEnd - arrayStart - 1);

        size_t pos = 0;
        while (pos < arrayContent.size())
        {
            size_t quoteStart = arrayContent.find(L'"', pos);
            if (quoteStart == std::wstring::npos)
                break;

            size_t quoteEnd = quoteStart + 1;
            while (quoteEnd < arrayContent.size())
            {
                if (arrayContent[quoteEnd] == L'\\' && quoteEnd + 1 < arrayContent.size())
                {
                    quoteEnd += 2;
                }
                else if (arrayContent[quoteEnd] == L'"')
                {
                    break;
                }
                else
                {
                    ++quoteEnd;
                }
            }

            if (quoteEnd >= arrayContent.size())
                break;

            std::wstring value = arrayContent.substr(quoteStart + 1, quoteEnd - quoteStart - 1);

            std::wstring unescaped;
            for (size_t i = 0; i < value.size(); ++i)
            {
                if (value[i] == L'\\' && i + 1 < value.size())
                {
                    switch (value[i + 1])
                    {
                    case L'"': unescaped += L'"'; break;
                    case L'\\': unescaped += L'\\'; break;
                    case L'n': unescaped += L'\n'; break;
                    case L'r': unescaped += L'\r'; break;
                    case L't': unescaped += L'\t'; break;
                    default: unescaped += value[i + 1]; break;
                    }
                    ++i;
                }
                else
                {
                    unescaped += value[i];
                }
            }

            failed.push_back(unescaped);
            pos = quoteEnd + 1;
        }

        return true;
    }
}
