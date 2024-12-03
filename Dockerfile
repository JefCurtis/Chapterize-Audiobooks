# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install ffmpeg and other dependencies
RUN apt-get update && apt-get install -y ffmpeg libatomic1

# Copy the requirements files into the container
COPY requirements.txt requirements-api.txt ./

# Install the dependencies specified in requirements.txt files
RUN pip install --no-cache-dir -r requirements.txt -r requirements-api.txt

# Copy the rest of the application code into the container
COPY . .

# Expose port 8000 for the FastAPI server
EXPOSE 8000

# Define the entrypoint to start the FastAPI server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
