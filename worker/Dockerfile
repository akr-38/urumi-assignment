FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (curl for downloading binaries)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

# Install Helm
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 && \
    chmod 700 get_helm.sh && \
    ./get_helm.sh && \
    rm get_helm.sh

RUN helm repo add bitnami https://charts.bitnami.com/bitnami && \
    helm repo update

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
