Here's an updated version of the `README.md` file for running tests on the `django-recipe-app-api` project using Docker Compose:

## Django Recipe App API

This is a sample Django project for managing recipes with REST API endpoints. It is built using Django, Django REST framework, and Docker.

## Prerequisites

Before running the project, you need to have Docker and Docker Compose installed on your machine. You can download and install them from the official Docker website: <https://www.docker.com/get-started>.

## How to run the project

1. Clone the repository to your local machine:

   ```
   git clone https://github.com/AvishkaUmesh/django-recipe-app-api.git
   ```

2. Change to the project directory:

   ```
   cd django-recipe-app-api
   ```

3. Build and run the Docker containers:

   ```
   docker-compose up -d --build
   ```

4. Run the database migrations:

   ```
   docker-compose run --rm app sh -c "python manage.py migrate"
   ```

5. Create a superuser account:

   ```
   docker-compose run --rm app sh -c "python manage.py createsuperuser"
   ```

6. You can now access the API at <http://localhost:8000/api/docs/>. The admin interface is available at <http://localhost:8000/admin/>.

7. To run the tests, use the following command:

   ```
   docker-compose run --rm app sh -c "python manage.py test"
   ```

That's it! You now have a running instance of the Django Recipe App API project with tests executed using Docker Compose.
