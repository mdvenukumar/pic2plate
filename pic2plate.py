import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
from tavily import TavilyClient
import pandas as pd

GEMINI = st.secrets["GEMINI"]
TAVILY = st.secrets["TAVILY"]
# Configure Gemini API
genai.configure(api_key=GEMINI)

# Configure Tavily API
tavily = TavilyClient(api_key=TAVILY)

st.set_page_config(page_title="PIC 2 PLATE", page_icon="🐰")
# Create the Gemini model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Custom CSS
st.markdown("""
<style>
.big-font {
    font-size:30px !important;
    font-weight: bold;
    text-align: center;
}
.stButton>button {
    width: 100%;
}
.stVideo > div {
    height: 300px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">🐰 PIC2PLATE - AI Recipe Generator</p>', unsafe_allow_html=True)

# Sidebar for input options
with st.sidebar:
    st.subheader("Input Options")
    input_method = st.radio("Choose input method:", ["Text", "Image"])
    
    if input_method == "Text":
        ingredients = st.text_area("Enter available ingredients (comma-separated):")
    else:
        uploaded_file = st.file_uploader("Upload an image of food items", type=["jpg", "jpeg", "png"])
    
    dietary_restrictions = st.multiselect("Select dietary restrictions:", 
                                          ["No Restrictions", "Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Nut-free"])
    cuisine_preference = st.selectbox("Choose cuisine preference:", 
                                      ["Any", "Italian", "Mexican", "Chinese", "Indian", "Japanese", "Mediterranean"])
    language_preference = st.selectbox("Choose language for YouTube videos:", 
                                       ["English", "Hindi", "Telugu"])

if st.button("Generate Recipe"):
    with st.spinner('Generating your recipe 😇'):
        st.balloons()
        if (input_method == "Text" and not ingredients) or (input_method == "Image" and not uploaded_file):
            st.warning("Please enter ingredients or upload an image.")
        else:
            try:
                if input_method == "Text":
                    chat_session = model.start_chat()
                    prompt = f"""
                    Generate a detailed recipe based on the following:
                    - Ingredients: {ingredients}
                    - Dietary restrictions: {', '.join(dietary_restrictions)}
                    - Cuisine preference: {cuisine_preference}
                    
                    The recipe should include:
                    1. Recipe name
                    2. Detailed ingredients list with quantities
                    3. Comprehensive step-by-step cooking instructions
                    4. Nutritional information per serving (including calories, proteins, carbohydrates, fats, vitamins, and minerals)
                    5. Estimated serving size and number of servings
                    6. Alternative ingredient suggestions for dietary restrictions
                    7. Tips for cooking and presentation
                    8. Any cultural or historical background related to the dish
                    """
                    response = chat_session.send_message(prompt)
                else:  # Image input
                    image = Image.open(uploaded_file)
                    
                    if image.mode != "RGB":
                        image = image.convert("RGB")
                    
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='JPEG')
                    img_bytes = img_byte_arr.getvalue()

                    chat_session = model.start_chat()
                    image_prompt = "What food items can you see in this image? If there are no food items, clearly state that no food items are present."
                    image_parts = [
                        image_prompt,
                        {"mime_type": "image/jpeg", "data": img_bytes}
                    ]
                    image_response = chat_session.send_message(image_parts)
                    
                    # Check if food items were found
                    if "no food items" in image_response.text.lower():
                        st.error("No food items were detected in the uploaded image. Please upload an image containing food items or ingredients.")
                        st.stop()  # Stop further execution
                    
                    prompt = f"""
                    Based on the food items in the image ({image_response.text}), generate a detailed recipe.
                    Consider these dietary restrictions: {', '.join(dietary_restrictions)}
                    The preferred cuisine style is: {cuisine_preference}
                    
                    The recipe should include:
                    1. Recipe name
                    2. Detailed ingredients list with quantities
                    3. Comprehensive step-by-step cooking instructions in detail
                    4. Nutritional information per serving (including calories, proteins, carbohydrates, fats, vitamins, and minerals)
                    5. Estimated serving size and number of servings
                    6. Alternative ingredient suggestions for dietary restrictions
                    7. Tips for cooking and presentation
                    8. Any cultural or historical background related to the dish
                    """
                    
                    response = chat_session.send_message(prompt)

                st.subheader("Generated Recipe:")
                st.write(response.text)

                # Extract recipe name from the generated content
                recipe_name = response.text.split('\n')[0].strip()

                # Extract nutritional information and present it in a table
                nutritional_info_start = response.text.find("Nutritional information per serving:")
                nutritional_info_end = response.text.find("Alternative ingredient suggestions:")
                if nutritional_info_start != -1 and nutritional_info_end != -1:
                    nutritional_info = response.text[nutritional_info_start + len("Nutritional information per serving:"):nutritional_info_end].strip()

                    if nutritional_info:
                        st.subheader("Nutritional Information (Estimated):")
                        nutritional_info_lines = nutritional_info.split('\n')
                        nutrition_dict = {}

                        for line in nutritional_info_lines:
                            if ':' in line:
                                key, value = line.split(':', 1)
                                nutrition_dict[key.strip()] = value.strip()

                        if nutrition_dict:
                            nutrition_df = pd.DataFrame(list(nutrition_dict.items()), columns=['Nutrient', 'Amount'])
                            st.table(nutrition_df)
                        else:
                            st.write("Nutritional information is not available in a readable format.")
                    else:
                        st.write("No nutritional information found.")
                else:
                    st.write("Nutritional information section is missing.")

                # Fetch YouTube video recommendations
                video_query = f"{recipe_name} recipe {language_preference}"
                video_response = tavily.search(
                    query=video_query, 
                    search_depth="basic",
                    include_domains=["youtube.com"],
                    max_results=4
                )

                st.subheader("YouTube Video Recommendations:")
                if 'results' in video_response and len(video_response['results']) > 0:
                    for i in range(0, len(video_response['results']), 2):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if i < len(video_response['results']):
                                st.write(f"{video_response['results'][i]['title']}")
                                st.video(video_response['results'][i]['url'])
                        
                        with col2:
                            if i + 1 < len(video_response['results']):
                                st.write(f"{video_response['results'][i+1]['title']}")
                                st.video(video_response['results'][i+1]['url'])
                else:
                    st.write("No YouTube videos found for this recipe.")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

st.markdown("---")
st.write("Note: This is a prototype. Always verify recipes, nutritional information, and video content.")

hide_streamlit_style = """
            <style>
            [data-testid="stToolbar"] {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)