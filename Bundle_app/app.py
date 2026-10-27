import streamlit as st
import tempfile
import zipfile
from analysis import analyze_folder

st.title("Actin Bundle Counter")
st.write("Create folders with the images from each condition"
         "Put the condition folders in a Zip file for the app to run")
uploaded = st.file_uploader("Upload a .zip", type="zip")

#putting the two buttons next to eachother
col1, col2 = st.columns(2)
run = col1.button("Run")
stop = col2.button("Stop analysis")

if stop:
    st.info("Analysis Stopped")

if run:
    if uploaded is None:
        st.warning("Upload a zip first.")
    else:
        st.session_state.pop("results", None)   # clear old results so they aren't mistaken for new ones
        bar = st.progress(0, text="Starting...")

        def update(done, total):
            bar.progress(done / total, text=f"{done} of {total} images")

        with tempfile.TemporaryDirectory() as tmp:
            zipfile.ZipFile(uploaded).extractall(tmp)
            df = analyze_folder(tmp, progress=update)
        st.session_state["results"] = df

if "results" in st.session_state:
    df = st.session_state["results"]
    st.dataframe(df)
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False),
        file_name="results.csv",
    )
