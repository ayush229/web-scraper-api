# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy all code to the working directory
COPY . .

# Install dependencies (update requirements.txt if not present)
RUN pip install --no-cache-dir flask flask-cors together

# Expose the port Flask runs on
EXPOSE 8000

# Start the Flask application
CMD ["python", "main.py"]
