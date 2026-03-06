import os
import django
import sys
from django.test import Client
from django.urls import reverse

# Setup Django
sys.path.append('d:/mixmint2.0')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User

client = Client(HTTP_HOST='localhost')

def test_registration():
    print("--- Phase 1: Auth & Registration Tests ---")
    
    # Clean up any existing test user
    User.objects.filter(email='test@example.com').delete()
    User.objects.filter(email='fake@mailinator.com').delete()

    print("\n1.1.1 Valid Registration")
    response = client.post(reverse('signup'), {
        'full_name': 'Test User',
        'email': 'test@example.com',
        'password': 'StrongPassword123!',
        'csrfmiddlewaretoken': 'dummy' # bypassing CSRF for unit test client
    })
    print(f"Status: {response.status_code}") # Should be 302 redirect to dashboard
    
    print("\n1.1.2 Disposable Email Registration")
    response = client.post(reverse('signup'), {
        'full_name': 'Hacker Man',
        'email': 'fake@mailinator.com',
        'password': 'StrongPassword123!',
    })
    print(f"Status: {response.status_code}") # Should stay on 200 with error
    print("Messages:", [m.message for m in response.context.get('messages', [])]) if hasattr(response, 'context') and response.context else print("No context")

    print("\n1.1.3 Duplicate Email Registration")
    response = client.post(reverse('signup'), {
        'full_name': 'Test User Two',
        'email': 'test@example.com',
        'password': 'StrongPassword123!',
    })
    print(f"Status: {response.status_code}")
    print("Messages:", [m.message for m in response.context.get('messages', [])]) if hasattr(response, 'context') and response.context else print("No context")

    print("\n1.1.4 Weak Password Registration")
    response = client.post(reverse('signup'), {
        'full_name': 'Test User Three',
        'email': 'test3@example.com',
        'password': 'weak',
    })
    print(f"Status: {response.status_code}")
    print("Messages:", [m.message for m in response.context.get('messages', [])]) if hasattr(response, 'context') and response.context else print("No context")

    print("\n1.1.6 Empty Form Submission")
    response = client.post(reverse('signup'), {})
    print(f"Status: {response.status_code}")
    print("Messages:", [m.message for m in response.context.get('messages', [])]) if hasattr(response, 'context') and response.context else print("No context")

    print("\n--- Login Tests ---")
    print("1.3.1 Valid Login")
    response = client.post(reverse('login'), {
        'username': 'test@example.com',
        'password': 'StrongPassword123!'
    })
    print(f"Status: {response.status_code}") # 302

    print("1.3.2 Wrong Password")
    response = client.post(reverse('login'), {
        'username': 'test@example.com',
        'password': 'WrongPassword123!'
    })
    print(f"Status: {response.status_code}") # 200
    print("Messages:", [m.message for m in response.context.get('messages', [])]) if hasattr(response, 'context') and response.context else print("No context")

    print("1.3.3 Unregistered Email")
    response = client.post(reverse('login'), {
        'username': 'ghost@example.com',
        'password': 'StrongPassword123!'
    })
    print(f"Status: {response.status_code}") # 200
    print("Messages:", [m.message for m in response.context.get('messages', [])]) if hasattr(response, 'context') and response.context else print("No context")


if __name__ == '__main__':
    test_registration()
