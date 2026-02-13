
# Medical App Exams

**Medical App Exams** is a robust microservice designed to manage laboratory test results. Part of the broader **Medical App** ecosystem, this service handles the registration of exam data and provides a secure way for patients to download their results.

Built with performance and scalability in mind, it follows the best practices for independent microservices development.

## 🚀 Technologies

* **Python 3.12**: The latest features for high-performance backend logic.
* **FastAPI**: Modern, fast (high-performance) web framework for building APIs.
* **PostgreSQL (AWS)**: Relational database hosted on AWS, utilizing **advanced SQL queries** for optimized data retrieval.
* **Docker**: Fully containerized application for consistent deployment.

## 🛠️ Key Features

* **Result Registration**: Secure endpoints to input laboratory exam data.
* **Result Download**: Streamlined process for patients to access and download their medical reports.
* **Independent Architecture**: Designed to operate autonomously within a microservices ecosystem.
* **Advanced Data Handling**: Optimized PostgreSQL queries to ensure speed even with complex datasets.

## 🏗️ Architecture & Best Practices

This project adheres to industry-standard microservices principles:

* **Single Responsibility**: Focused exclusively on exam management.
* **Independence**: Decoupled from other services for easy scaling and maintenance.
* **Containerization**: Ready for orchestration (like Kubernetes) via Docker.

## 📦 How to Run

1. **Clone the repository**:
```bash
git clone https://github.com/your-username/medical-app-exams.git

```


2. **Set up environment variables**:
Configure your AWS PostgreSQL credentials in a `.env` file.
3. **Run with Docker**:
```bash
docker build -t medical-app-exams .
docker run -p 8000:8000 medical-app-exams

```
4. Alternative:
   Run:
   
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```



<img width="1242" height="609" alt="image" src="https://github.com/user-attachments/assets/d893941a-1de1-40f2-bd02-0821858a8889" />


<img width="1237" height="620" alt="image" src="https://github.com/user-attachments/assets/2616e28f-ba7c-4d9b-8b07-a168f0c2b4db" />

<img width="1237" height="620" alt="image" src="https://github.com/user-attachments/assets/32e428a9-b7af-403b-975d-aabd51f67c6a" />

<img width="1237" height="620" alt="image" src="https://github.com/user-attachments/assets/bf348e31-6699-44b7-b01e-5fc5825e4332" />




## ✒️ Authorship & Contributions

This project is an **exclusive contribution by Lester Cerioli**.

---

