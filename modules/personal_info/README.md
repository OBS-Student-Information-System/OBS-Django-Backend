# Personal Information (Özlük Bilgileri) Module

## Overview
This module handles fetching the student's personal information from OBS, specifically the data found on the "Özlük Bilgileri / Adres Bilgileri" page. It conforms to the underlying database schema while returning a structured JSON response through the Scraper-Service pattern.

## 📌 Scraper Logic: "The Caller Pattern"
This module uses OBS's "Iframe page loading" logic (Caller) heavily. 

*   **URL:** `https://obs.ozal.edu.tr/oibs/std/caller.aspx?curPage=100` (Caller) -> `ogr_ozluk.aspx` (Frame)
*   **Page ID:** `100` (Özlük Bilgileri page)
*   **Logic:**
    1. Hit `caller.aspx?curPage=100` with `Sec-Fetch-Dest: document` to setup the frame loading session.
    2. Hit `ogr_ozluk.aspx` with `Sec-Fetch-Dest: iframe` to retrieve the actual form data.
    3. Parse the inputs (`txtCep1`, `txtAileAdres`, `txtBankaIBAN`, etc.) via BeautifulSoup.

## 🚨 Critical Headers
The following headers are **REQUIRED** for this request to succeed:
```python
{
    'Referer': 'https://obs.ozal.edu.tr/oibs/std/index.aspx?curOp=0',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
}
```

## Data Envelope
The module maps HTML variables to an English JSON response envelope compatible with standard mobile endpoints:
```json
{
  "success": true,
  "data": {
    "contact": {
      "phone1": "",
      "phone2": "",
      "email1": "",
      "email2": ""
    },
    ...
  }
}
```
