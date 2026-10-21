import streamlit as st

# Set up the title and a simple subheader
st.title("🚀 My New Streamlit App")
st.subheader("Welcome to your data dashboard!")

# Text output
st.write("This application was built in minutes using Python.")

# Interactive slider widget
age = st.slider("Yaşını seç", min_value=0, max_value=100, value=25)
st.success(f"You selected: {age} years old")
