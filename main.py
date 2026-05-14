import requests


def main():
    print("Hello from rigel-sender!")

    title = "Is it better to learn Docker before Kubernetes?"
    content = "I’m trying to get into cloud-native development, but the ecosystem feels huge. Should I fully understand Docker first, or learn both together?"
    
    url = "http://127.0.0.1:3000/api/v1/posts"
    headers = {
        "Authorization": "Bearer 8a0897dd73c1e689e4cd779a51f77c21966545ebe07594dc",
        "Content-Type": "application/json"
    }
    data = {
        "post": {
            "title": title,
            "content": content
        }
    }

    response = requests.post(url, json=data, headers=headers)
    print(response.json())



if __name__ == "__main__":
    main()
