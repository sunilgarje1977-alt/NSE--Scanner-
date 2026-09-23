import streamlit as st
import pandas as pd

st.set_page_config(page_title="NSE Scanner", layout="wide")
st.title("🚀 NSE Scanner - Live")
st.success("GitHub to Streamlit Deploy Success!")

st.write("तुझा Scanner इथे लाईव्ह होईल. Telegram / Angel Keys नंतर टाकूया.")

if st.button("Test Scan"):
    st.balloons()
    st.write("✅ RELIANCE - BUY Signal (Test)")
    st.write("✅ SBIN - BUY Signal (Test)")
