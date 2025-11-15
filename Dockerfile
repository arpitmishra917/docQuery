# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
# COPY .env .
COPY src/ src/
COPY data/ data/

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose ports
EXPOSE 8000
EXPOSE 8501

# Start both FastAPI and Streamlit
CMD ["bash", "-c", "uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000 & streamlit run src/ui/streamlit_app.py --server.port 8501 & wait"]