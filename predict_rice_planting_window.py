<<<<<<< HEAD
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- Location and Crop Calendar Settings ---
BULANDSHAHR_LATITUDE = 28.41
BULANDSHAHR_LONGITUDE = 77.85
CROP_NAME = "Rice"

# Rabi harvest period (preceding Kharif Rice planting)
RABI_HARVEST_START_MONTH = 2  # February
RABI_HARVEST_START_DAY = 15
RABI_HARVEST_END_MONTH = 4    # April
RABI_HARVEST_END_DAY = 30

# --- Rainfall Thresholds for Planting Window Categories (mm) ---
# Based on preceding Rabi harvest rainfall
RAINFALL_THRESHOLD_FOR_EARLY_MM = 25.0
RAINFALL_THRESHOLD_FOR_LATE_MM = 50.0 # Rain between EARLY and LATE is NORMAL

# --- Defined Planting Date Windows for Rice in Bulandshahr ---
# These are estimates and can be adjusted with local expertise
PLANTING_WINDOWS = {
    "Early": {"start_day": 10, "start_month": 6, "end_day": 30, "end_month": 6, "display": "June 10th - June 30th"},
    "Normal": {"start_day": 20, "start_month": 6, "end_day": 15, "end_month": 7, "display": "June 20th - July 15th"},
    "Late": {"start_day": 5, "start_month": 7, "end_day": 31, "end_month": 7, "display": "July 5th - July 31st"}
}

# --- Function to Fetch Historical Precipitation Data ---
def get_historical_precipitation(latitude, longitude, start_date_str, end_date_str):
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "daily": "precipitation_sum",
        "timezone": "Asia/Kolkata"
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if 'daily' in data and 'precipitation_sum' in data['daily']:
            total_precipitation = sum(p if p is not None else 0 for p in data['daily']['precipitation_sum'])
            return total_precipitation
        else:
            st.error("Precipitation data format incorrect in API response.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return None
    except KeyError:
        st.error("Could not find expected data keys in the API response.")
        return None

# --- Prediction Function ---
def predict_rice_planting_window(year):
    try:
        harvest_start_date_str = datetime(year, RABI_HARVEST_START_MONTH, RABI_HARVEST_START_DAY).strftime('%Y-%m-%d')
        harvest_end_date_str = datetime(year, RABI_HARVEST_END_MONTH, RABI_HARVEST_END_DAY).strftime('%Y-%m-%d')
    except ValueError:
        st.error(f"Invalid date configuration for Rabi harvest in year {year}.")
        return None

    st.write(f"Fetching rainfall data for Bulandshahr ({harvest_start_date_str} to {harvest_end_date_str})...")
    total_rabi_harvest_rain = get_historical_precipitation(
        BULANDSHAHR_LATITUDE,
        BULANDSHAHR_LONGITUDE,
        harvest_start_date_str,
        harvest_end_date_str
    )

    if total_rabi_harvest_rain is not None:
        st.write(f"Total rainfall during preceding Rabi harvest: {total_rabi_harvest_rain:.2f} mm")

        predicted_category = ""
        suggested_dates = ""
        key_factors_list = []
        confidence_score = 0.75 # Base confidence

        if total_rabi_harvest_rain < RAINFALL_THRESHOLD_FOR_EARLY_MM:
            predicted_category = "Early"
            suggested_dates = PLANTING_WINDOWS["Early"]["display"]
            key_factors_list.append(f"Low Rabi harvest rainfall ({total_rabi_harvest_rain:.2f} mm, below {RAINFALL_THRESHOLD_FOR_EARLY_MM} mm) suggests fields may be ready sooner.")
            confidence_score = 0.70
        elif total_rabi_harvest_rain <= RAINFALL_THRESHOLD_FOR_LATE_MM:
            predicted_category = "Normal"
            suggested_dates = PLANTING_WINDOWS["Normal"]["display"]
            key_factors_list.append(f"Moderate Rabi harvest rainfall ({total_rabi_harvest_rain:.2f} mm) indicates typical conditions for standard planting.")
            confidence_score = 0.80
        else: # total_rabi_harvest_rain > RAINFALL_THRESHOLD_FOR_LATE_MM
            predicted_category = "Late"
            suggested_dates = PLANTING_WINDOWS["Late"]["display"]
            key_factors_list.append(f"High Rabi harvest rainfall ({total_rabi_harvest_rain:.2f} mm, above {RAINFALL_THRESHOLD_FOR_LATE_MM} mm) may delay field preparation due to excessive moisture.")
            confidence_score = 0.70

        # Adjust confidence for future/incomplete data
        current_datetime = datetime.now()
        harvest_end_datetime = datetime(year, RABI_HARVEST_END_MONTH, RABI_HARVEST_END_DAY)
        if harvest_end_datetime > current_datetime:
            warning_msg = "WARNING: Rabi harvest data period for this year is "
            if datetime(year, RABI_HARVEST_START_MONTH,RABI_HARVEST_START_DAY) > current_datetime:
                 warning_msg += "entirely in the future. Prediction is speculative."
                 confidence_score *= 0.5
            else:
                 warning_msg += "not yet complete. Prediction based on partial data."
                 confidence_score *= 0.7
            key_factors_list.append(warning_msg)

        return {
            'year': year,
            'crop': CROP_NAME,
            'predicted_category': predicted_category,
            'suggested_planting_window_dates': suggested_dates, # Added this
            'confidence': confidence_score,
            'key_factors': key_factors_list,
            'data_period_analysed': f"{harvest_start_date_str} to {harvest_end_date_str}",
            'total_rabi_harvest_rain_mm': total_rabi_harvest_rain
        }
    else:
        st.error("Could not retrieve rainfall data. Prediction is not possible.")
        return None

# --- Streamlit App Interface ---
def run_rice_predictor_app():
    st.set_page_config(page_title=f"{CROP_NAME} Planting Predictor", layout="wide")
    st.title(f"🌾 {CROP_NAME} Planting Window Predictor (Bulandshahr, UP) 🌦️")

    st.markdown(f"""
    This tool predicts the **{CROP_NAME} planting window category (Early, Normal, or Late)** and suggests **specific date ranges** for Bulandshahr.
    The prediction is based on rainfall during the preceding Rabi crop harvest.
    """)

    st.sidebar.header("Select Year for Prediction")
    current_year = datetime.now().year
    year_options = list(range(current_year - 5, current_year + 3)) # Past 5, current, next 2

    selected_year = st.sidebar.selectbox(
        f"Select year for {CROP_NAME} planting prediction:",
        options=year_options,
        index=year_options.index(current_year)
    )

    if st.sidebar.button(f"Predict {CROP_NAME} Planting Window"):
        if selected_year:
            st.subheader(f"Prediction for {CROP_NAME} Planting in {selected_year}:")
            prediction_output = predict_rice_planting_window(selected_year)

            if prediction_output:
                st.markdown(f"**Predicted Window Category:** <h3 style='color: #006400;'>{prediction_output['predicted_category']}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Suggested Planting Dates:** <h4 style='color: #00008B;'>{prediction_output['suggested_planting_window_dates']}</h4>", unsafe_allow_html=True)

                st.write(f"**Confidence in this prediction:** {prediction_output['confidence']:.0%}")
                st.progress(prediction_output['confidence'])

                st.markdown("**Key Factors Considered:**")
                for factor in prediction_output['key_factors']:
                    st.markdown(f"- {factor}")

                st.info(f"""
                **Data Period Analysed:** {prediction_output['data_period_analysed']} (Rabi harvest)
                **Total Rainfall in this Period:** {prediction_output['total_rabi_harvest_rain_mm']:.2f} mm
                """)
                st.markdown("---")
                st.success(f"Remember to also consider current weather, soil moisture, and local agricultural advice when making your final {CROP_NAME} planting decisions.")
        else:
            st.sidebar.error("Please select a year.")

    st.sidebar.markdown("---")
    st.sidebar.header("About This Tool")
    st.sidebar.info(f"""
    Predicts {CROP_NAME} planting window for Bulandshahr based on Rabi harvest rainfall ({RABI_HARVEST_START_DAY} Feb - {RABI_HARVEST_END_DAY} Apr).
    - Rain < {RAINFALL_THRESHOLD_FOR_EARLY_MM}mm: Early
    - {RAINFALL_THRESHOLD_FOR_EARLY_MM}mm - {RAINFALL_THRESHOLD_FOR_LATE_MM}mm Rain: Normal
    - Rain > {RAINFALL_THRESHOLD_FOR_LATE_MM}mm: Late
    **Disclaimer:** Use as guidance. Local conditions are key.
    """)

if __name__ == "__main__":
=======
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- Location and Crop Calendar Settings ---
BULANDSHAHR_LATITUDE = 28.41
BULANDSHAHR_LONGITUDE = 77.85
CROP_NAME = "Rice"

# Rabi harvest period (preceding Kharif Rice planting)
RABI_HARVEST_START_MONTH = 2  # February
RABI_HARVEST_START_DAY = 15
RABI_HARVEST_END_MONTH = 4    # April
RABI_HARVEST_END_DAY = 30

# --- Rainfall Thresholds for Planting Window Categories (mm) ---
# Based on preceding Rabi harvest rainfall
RAINFALL_THRESHOLD_FOR_EARLY_MM = 25.0
RAINFALL_THRESHOLD_FOR_LATE_MM = 50.0 # Rain between EARLY and LATE is NORMAL

# --- Defined Planting Date Windows for Rice in Bulandshahr ---
# These are estimates and can be adjusted with local expertise
PLANTING_WINDOWS = {
    "Early": {"start_day": 10, "start_month": 6, "end_day": 30, "end_month": 6, "display": "June 10th - June 30th"},
    "Normal": {"start_day": 20, "start_month": 6, "end_day": 15, "end_month": 7, "display": "June 20th - July 15th"},
    "Late": {"start_day": 5, "start_month": 7, "end_day": 31, "end_month": 7, "display": "July 5th - July 31st"}
}

# --- Function to Fetch Historical Precipitation Data ---
def get_historical_precipitation(latitude, longitude, start_date_str, end_date_str):
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "daily": "precipitation_sum",
        "timezone": "Asia/Kolkata"
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if 'daily' in data and 'precipitation_sum' in data['daily']:
            total_precipitation = sum(p if p is not None else 0 for p in data['daily']['precipitation_sum'])
            return total_precipitation
        else:
            st.error("Precipitation data format incorrect in API response.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return None
    except KeyError:
        st.error("Could not find expected data keys in the API response.")
        return None

# --- Prediction Function ---
def predict_rice_planting_window(year):
    try:
        harvest_start_date_str = datetime(year, RABI_HARVEST_START_MONTH, RABI_HARVEST_START_DAY).strftime('%Y-%m-%d')
        harvest_end_date_str = datetime(year, RABI_HARVEST_END_MONTH, RABI_HARVEST_END_DAY).strftime('%Y-%m-%d')
    except ValueError:
        st.error(f"Invalid date configuration for Rabi harvest in year {year}.")
        return None

    st.write(f"Fetching rainfall data for Bulandshahr ({harvest_start_date_str} to {harvest_end_date_str})...")
    total_rabi_harvest_rain = get_historical_precipitation(
        BULANDSHAHR_LATITUDE,
        BULANDSHAHR_LONGITUDE,
        harvest_start_date_str,
        harvest_end_date_str
    )

    if total_rabi_harvest_rain is not None:
        st.write(f"Total rainfall during preceding Rabi harvest: {total_rabi_harvest_rain:.2f} mm")

        predicted_category = ""
        suggested_dates = ""
        key_factors_list = []
        confidence_score = 0.75 # Base confidence

        if total_rabi_harvest_rain < RAINFALL_THRESHOLD_FOR_EARLY_MM:
            predicted_category = "Early"
            suggested_dates = PLANTING_WINDOWS["Early"]["display"]
            key_factors_list.append(f"Low Rabi harvest rainfall ({total_rabi_harvest_rain:.2f} mm, below {RAINFALL_THRESHOLD_FOR_EARLY_MM} mm) suggests fields may be ready sooner.")
            confidence_score = 0.70
        elif total_rabi_harvest_rain <= RAINFALL_THRESHOLD_FOR_LATE_MM:
            predicted_category = "Normal"
            suggested_dates = PLANTING_WINDOWS["Normal"]["display"]
            key_factors_list.append(f"Moderate Rabi harvest rainfall ({total_rabi_harvest_rain:.2f} mm) indicates typical conditions for standard planting.")
            confidence_score = 0.80
        else: # total_rabi_harvest_rain > RAINFALL_THRESHOLD_FOR_LATE_MM
            predicted_category = "Late"
            suggested_dates = PLANTING_WINDOWS["Late"]["display"]
            key_factors_list.append(f"High Rabi harvest rainfall ({total_rabi_harvest_rain:.2f} mm, above {RAINFALL_THRESHOLD_FOR_LATE_MM} mm) may delay field preparation due to excessive moisture.")
            confidence_score = 0.70

        # Adjust confidence for future/incomplete data
        current_datetime = datetime.now()
        harvest_end_datetime = datetime(year, RABI_HARVEST_END_MONTH, RABI_HARVEST_END_DAY)
        if harvest_end_datetime > current_datetime:
            warning_msg = "WARNING: Rabi harvest data period for this year is "
            if datetime(year, RABI_HARVEST_START_MONTH,RABI_HARVEST_START_DAY) > current_datetime:
                 warning_msg += "entirely in the future. Prediction is speculative."
                 confidence_score *= 0.5
            else:
                 warning_msg += "not yet complete. Prediction based on partial data."
                 confidence_score *= 0.7
            key_factors_list.append(warning_msg)

        return {
            'year': year,
            'crop': CROP_NAME,
            'predicted_category': predicted_category,
            'suggested_planting_window_dates': suggested_dates, # Added this
            'confidence': confidence_score,
            'key_factors': key_factors_list,
            'data_period_analysed': f"{harvest_start_date_str} to {harvest_end_date_str}",
            'total_rabi_harvest_rain_mm': total_rabi_harvest_rain
        }
    else:
        st.error("Could not retrieve rainfall data. Prediction is not possible.")
        return None

# --- Streamlit App Interface ---
def run_rice_predictor_app():
    st.set_page_config(page_title=f"{CROP_NAME} Planting Predictor", layout="wide")
    st.title(f"🌾 {CROP_NAME} Planting Window Predictor (Bulandshahr, UP) 🌦️")

    st.markdown(f"""
    This tool predicts the **{CROP_NAME} planting window category (Early, Normal, or Late)** and suggests **specific date ranges** for Bulandshahr.
    The prediction is based on rainfall during the preceding Rabi crop harvest.
    """)

    st.sidebar.header("Select Year for Prediction")
    current_year = datetime.now().year
    year_options = list(range(current_year - 5, current_year + 3)) # Past 5, current, next 2

    selected_year = st.sidebar.selectbox(
        f"Select year for {CROP_NAME} planting prediction:",
        options=year_options,
        index=year_options.index(current_year)
    )

    if st.sidebar.button(f"Predict {CROP_NAME} Planting Window"):
        if selected_year:
            st.subheader(f"Prediction for {CROP_NAME} Planting in {selected_year}:")
            prediction_output = predict_rice_planting_window(selected_year)

            if prediction_output:
                st.markdown(f"**Predicted Window Category:** <h3 style='color: #006400;'>{prediction_output['predicted_category']}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Suggested Planting Dates:** <h4 style='color: #00008B;'>{prediction_output['suggested_planting_window_dates']}</h4>", unsafe_allow_html=True)

                st.write(f"**Confidence in this prediction:** {prediction_output['confidence']:.0%}")
                st.progress(prediction_output['confidence'])

                st.markdown("**Key Factors Considered:**")
                for factor in prediction_output['key_factors']:
                    st.markdown(f"- {factor}")

                st.info(f"""
                **Data Period Analysed:** {prediction_output['data_period_analysed']} (Rabi harvest)
                **Total Rainfall in this Period:** {prediction_output['total_rabi_harvest_rain_mm']:.2f} mm
                """)
                st.markdown("---")
                st.success(f"Remember to also consider current weather, soil moisture, and local agricultural advice when making your final {CROP_NAME} planting decisions.")
        else:
            st.sidebar.error("Please select a year.")

    st.sidebar.markdown("---")
    st.sidebar.header("About This Tool")
    st.sidebar.info(f"""
    Predicts {CROP_NAME} planting window for Bulandshahr based on Rabi harvest rainfall ({RABI_HARVEST_START_DAY} Feb - {RABI_HARVEST_END_DAY} Apr).
    - Rain < {RAINFALL_THRESHOLD_FOR_EARLY_MM}mm: Early
    - {RAINFALL_THRESHOLD_FOR_EARLY_MM}mm - {RAINFALL_THRESHOLD_FOR_LATE_MM}mm Rain: Normal
    - Rain > {RAINFALL_THRESHOLD_FOR_LATE_MM}mm: Late
    **Disclaimer:** Use as guidance. Local conditions are key.
    """)

if __name__ == "__main__":
>>>>>>> e97d7d1b12d22b0a72c5ebb643a7cd9d55483526
    run_rice_predictor_app()