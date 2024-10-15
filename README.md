# Waste Backend FastAPI 
---
This project contains the backend infrastructure for a waste management application. The application leverages computer vision and machine learning to enable waste detection and classification, aiming to streamline waste processing and sorting.

## Overview
This backend system is designed to support the development of an AI-driven waste management application. It provides APIs for detecting and classifying waste types based on image inputs and integrates a YOLO model for optimized image recognition. Additionally, it includes endpoints for managing waste-related data, annotations, and integrations with the broader waste management ecosystem.


## Features
- **Waste Detection and Classification:** Detects various waste types and classifies them based on trained image models.
- **YOLO Integration:** Uses the YOLO model for efficient image recognition, tailored to waste management use cases.
- **API Development:** A comprehensive suite of RESTful APIs for interacting with the waste management system.
- **Data Management:*** Allows for CRUD operations on waste data and images.
- **Integration-Ready:** Built to integrate with frontend interfaces, databases, and mobile applications.

## Installation
To install and run this backend service locally, follow these steps:

1. Clone the Repository:

```bash
git clone https://github.com/javaidiqbal11/Waste_Backend_Dev.git
cd Waste_Backend_Dev
```
2. Install Dependencies: This project uses Python 3.12 and requires dependencies listed in the requirements.txt file.

```bash
pip install -r requirements.txt
```
3. Set Up YOLO Model: Download the pre-trained YOLO model and add it to the designated folder.

4. Configure Environment Variables: Create a .env file with necessary configurations for database connections and API keys.

5. Run the Application:

```bash
python app.py
```
