from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class UserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse('user-list')  # from DRF router

    def test_create_user_success(self):
        payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'secret123',
            'first_name': 'Alice',
            'last_name': 'Liddell',
        }
        res = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', res.data)
        user = User.objects.get(id=res.data['id'])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('secret123'))

    def test_create_user_rejects_admin_flags(self):
        payload = {
            'username': 'bob',
            'password': 'secret123',
            'is_staff': True,
        }
        res = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_non_admin_users(self):
        u1 = User.objects.create_user(username='u1', email='u1@example.com', password='p1')
        u2 = User.objects.create_user(username='u2', email='u2@example.com', password='p2')
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='adminpass')
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        usernames = [u['username'] for u in res.data]
        self.assertIn('u1', usernames)
        self.assertIn('u2', usernames)
        self.assertNotIn('admin', usernames)

    def test_retrieve_update_partial_delete_flow(self):
        # Create
        res = self.client.post(self.list_url, {'username': 'charlie', 'password': 'pw'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user_id = res.data['id']
        detail_url = reverse('user-detail', args=[user_id])
        # Retrieve
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'charlie')
        # Update
        res = self.client.put(detail_url, {'username': 'charlie2', 'password': 'pw2'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'charlie2')
        # Partial update
        res = self.client.patch(detail_url, {'first_name': 'C'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['first_name'], 'C')
        # Delete
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        # Ensure gone
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tester', email='tester@example.com', password='secret123'
        )
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')

    def test_login_with_username_success(self):
        res = self.client.post(self.login_url, {'email': 'tester', 'password': 'secret123'})
        # Expect redirect to home
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, '/')
        # Session created
        self.assertIn('_auth_user_id', self.client.session)
        # Default behavior (no remember): expire at browser close
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_with_email_success(self):
        res = self.client.post(self.login_url, {'email': 'tester@example.com', 'password': 'secret123', 'remember': 'on'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, '/')
        self.assertIn('_auth_user_id', self.client.session)
        # With remember, should be persistent
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_login_invalid_credentials(self):
        res = self.client.post(self.login_url, {'email': 'tester', 'password': 'wrong'})
        self.assertEqual(res.status_code, 400)
        # Error message rendered with 400 status
        self.assertContains(res, 'Invalid credentials', status_code=400)

    def test_logout_redirects_to_login(self):
        # First login
        self.client.post(self.login_url, {'email': 'tester', 'password': 'secret123'})
        self.assertIn('_auth_user_id', self.client.session)
        # Logout
        res = self.client.post(self.logout_url)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, self.login_url)
        # Session cleared
        self.assertNotIn('_auth_user_id', self.client.session)


class RegisterViewTests(TestCase):
    def setUp(self):
        self.register_url = reverse('register')

    def test_register_success(self):
        payload = {
            'first_name': 'Lan',
            'last_name': 'Anh',
            'email': 'lan.anh@example.com',
            'phone': '0900000000',
            'account_type': 'store',
            'store_name': 'Cua Hang ABC',
            'address': '123 ABC, HCM',
            'password': 'StrongPass1!',
            'password_confirm': 'StrongPass1!',
            'terms': 'on',
        }
        res = self.client.post(self.register_url, payload)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, '/')
        # User is created and logged in
        self.assertIn('_auth_user_id', self.client.session)
        user = User.objects.get(email='lan.anh@example.com')
        self.assertEqual(user.first_name, 'Lan')
        self.assertEqual(user.last_name, 'Anh')
        self.assertEqual(user.phone, '0900000000')
        self.assertEqual(user.account_type, 'store')
        self.assertEqual(user.store_name, 'Cua Hang ABC')
        self.assertTrue(user.check_password('StrongPass1!'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_register_password_mismatch(self):
        payload = {
            'first_name': 'Lan',
            'last_name': 'Anh',
            'email': 'lan2@example.com',
            'phone': '0900000001',
            'account_type': 'enterprise',
            'store_name': 'Cong ty XYZ',
            'password': 'StrongPass1!',
            'password_confirm': 'WrongConfirm',
            'terms': 'on',
        }
        res = self.client.post(self.register_url, payload)
        self.assertEqual(res.status_code, 400)
        self.assertContains(res, 'khớp', status_code=400)

    def test_register_duplicate_email(self):
        User.objects.create_user(username='u1', email='dup@example.com', password='secret123')
        payload = {
            'first_name': 'A',
            'last_name': 'B',
            'email': 'dup@example.com',
            'phone': '0900000002',
            'account_type': 'individual',
            'store_name': 'Self',
            'password': 'StrongPass1!',
            'password_confirm': 'StrongPass1!',
            'terms': 'on',
        }
        res = self.client.post(self.register_url, payload)
        self.assertEqual(res.status_code, 400)
        self.assertContains(res, 'Email đã được sử dụng', status_code=400)

    def test_register_requires_terms(self):
        payload = {
            'first_name': 'A',
            'last_name': 'B',
            'email': 'no-terms@example.com',
            'phone': '0900000003',
            'account_type': 'store',
            'store_name': 'Shop',
            'password': 'StrongPass1!',
            'password_confirm': 'StrongPass1!',
            # missing terms
        }
        res = self.client.post(self.register_url, payload)
        self.assertEqual(res.status_code, 400)
        self.assertContains(res, 'đồng ý với điều khoản', status_code=400)
