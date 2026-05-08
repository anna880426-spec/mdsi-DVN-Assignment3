# mdsi-DVN-Assignment3
Group project for MDSI assignment 3 


## Project Description
This project analyses bus performance data in Sydney, including on-time running, cancellations, and passenger trips across different regions and card types.


## File Structure
- `datacleaning.ipynb` — data cleaning notebook
- `data dictionary.xlsx` — description of all dataset columns
- `requirements.txt` — required Python packages
- `cleaned_df_bus.csv` — cleaned bus performance dataset
- `cleaned_df_models.csv` — cleaned models dataset
- `all_modes.csv` — raw data (all transport modes)
- `busperformance_reports_feb26.xlsx` — raw bus performance report

## How to Run
1. Open `datacleaning.ipynb` in Google Colab
2. Mount your Google Drive
3. Run all cells in order

## Data Source
Transport for NSW — Bus Performance Reports

## 🚀 Getting Started

Follow these steps to set up the project on your local machine.

### 1. Install Dependencies
Open your console/terminal and run the following command to install the necessary Python libraries:
```bash
pip install -r requirements.txt
```
### 2. Obtain a TfNSW API Key
Register: Create an account at the TfNSW Open Data Hub. -> https://opendata.transport.nsw.gov.au

Create Token: Navigate to your Profile, go to the API Tokens tab, then name and create an API Key.

### 3. Environment Configuration
Create a file named .env in the root directory (the same folder as your app.py). Add your API key to this file exactly as shown below:

```Plaintext
TRANSPORT_API_KEY = 'PASTE_API_KEY_HERE'
```
### 4. Run the Application
Ensure your console is in the correct directory, then execute:

```vash
streamlit run app.py