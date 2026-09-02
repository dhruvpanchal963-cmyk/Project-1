FITX UX Intelligence Dashboard

A Streamlit dashboard built directly from the supplied FITX raw event-log Excel files.

What is included

app.py — complete Streamlit dashboard

requirements.txt — Python dependencies

README.md — deployment instructions

data/ — the 21 supplied FITX .xlsx event datasets

Dashboard sections

Executive Overview

Audience & Devices

Navigation & Sankey

Conversion

Forms & Errors

Engagement

Exit & Scroll

Raw Data

Important

There is no upload-file option. The dashboard always reads the supplied files from data/.

Run locally

pip install -r requirements.txt
streamlit run app.py

Streamlit Cloud

Push the whole project folder to GitHub and set the main file to:

app.py

Keep the data folder in the same repository. Do not rename or remove the Excel files.

Data handling

The app reads timestamps, user IDs, session IDs, device, browser, referrer and event-specific fields directly from the supplied source files. It does not generate synthetic behavioral records.
