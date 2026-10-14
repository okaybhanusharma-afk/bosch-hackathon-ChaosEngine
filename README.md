# bosch-hackathon-2027

This repository contains our solution for the Bosch Hackathon 2027.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>/bosch-hackathon-2027.git
   cd bosch-hackathon-2027
   ```

2. **Set up the virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Get the Microservices Demo:**
   The `microservices-demo` folder is excluded from this repository because it is an external project. You need to clone it locally to the root directory of this project:
   ```bash
   git clone https://github.com/GoogleCloudPlatform/microservices-demo.git
   ```

5. **Run the Application:**
   ```bash
   streamlit run app.py
   ```
