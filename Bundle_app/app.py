import streamlit as st
import tempfile
import zipfile
from analysis import analyze_folder

st.title("Actin Bundle Counter")
st.write("Needs a zip folder with subfolders for each condition that are named accordingly with the images from each condition inside those subfolders")
uploaded = st.file_uploader("Upload a .zip", type="zip")

if st.button("Run"):
    if uploaded == None:
        st.warning("Upload a zip first")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            zipfile.ZipFile(uploaded).extractall(tmp)
            with st.spinner("Processing"):
                df = analyze_folder(tmp)
            st.session_state["results"] = df
if "results" in st.session_state:
    df = st.session_state["results"]
    st.dataframe(df)
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False),
        file_name="results.csv",
    )
    