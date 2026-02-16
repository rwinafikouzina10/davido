#!/bin/bash
# Run TruckParking Optimizer

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Streamlit
streamlit run app.py --server.port 8501
