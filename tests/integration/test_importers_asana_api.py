# -*- coding: utf-8 -*-
# Copyright (C) 2014-2016 Andrey Antukh <niwi@niwi.nz>
# Copyright (C) 2014-2016 Jesús Espino <jespinog@gmail.com>
# Copyright (C) 2014-2016 David Barragán <bameda@dbarragan.com>
# Copyright (C) 2014-2016 Alejandro Alonso <alejandro.alonso@kaleidos.net>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest
import json

from unittest import mock

from django.core.urlresolvers import reverse

from .. import factories as f
from taiga.importers import exceptions
from taiga.base.utils import json
from taiga.base import exceptions as exc


pytestmark = pytest.mark.django_db


def test_auth_url(client, settings):
    user = f.UserFactory.create()
    client.login(user)
    settings.ASANA_APP_CALLBACK_URL = "http://testserver/url"
    settings.ASANA_APP_ID = "test-id"
    settings.ASANA_APP_SECRET = "test-secret"

    url = reverse("importers-asana-auth-url")

    with mock.patch('taiga.importers.asana.api.AsanaImporter') as AsanaImporterMock:
        AsanaImporterMock.get_auth_url.return_value = "https://auth_url"
        response = client.get(url, content_type="application/json")
        assert AsanaImporterMock.get_auth_url.calledWith(settings.ASANA_APP_ID, settings.ASANA_APP_SECRET, settings.ASANA_APP_CALLBACK_URL)

    assert response.status_code == 200
    assert 'url' in response.data
    assert response.data['url'] == "https://auth_url"


def test_authorize(client, settings):
    user = f.UserFactory.create()
    client.login(user)

    authorize_url = reverse("importers-asana-authorize")

    with mock.patch('taiga.importers.asana.api.AsanaImporter') as AsanaImporterMock:
        AsanaImporterMock.get_access_token.return_value = "token"
        response = client.post(authorize_url, content_type="application/json", data=json.dumps({"code": "code"}))
        assert AsanaImporterMock.get_access_token.calledWith(settings.ASANA_APP_ID, settings.ASANA_APP_SECRET, "code")

    assert response.status_code == 200
    assert 'token' in response.data
    assert response.data['token'] == "token"


def test_authorize_without_code(client):
    user = f.UserFactory.create()
    client.login(user)

    authorize_url = reverse("importers-asana-authorize")

    response = client.post(authorize_url, content_type="application/json", data=json.dumps({}))

    assert response.status_code == 400
    assert 'token' not in response.data
    assert '_error_message' in response.data
    assert response.data['_error_message'] == "Code param needed"


def test_authorize_with_bad_verify(client, settings):
    user = f.UserFactory.create()
    client.login(user)

    authorize_url = reverse("importers-asana-authorize")

    with mock.patch('taiga.importers.asana.api.AsanaImporter') as AsanaImporterMock:
        AsanaImporterMock.get_access_token.side_effect = exceptions.InvalidRequest()
        response = client.post(authorize_url, content_type="application/json", data=json.dumps({"code": "bad"}))
        assert AsanaImporterMock.get_access_token.calledWith(settings.ASANA_APP_ID, settings.ASANA_APP_SECRET, "bad")

    assert response.status_code == 400
    assert 'token' not in response.data
    assert '_error_message' in response.data
    assert response.data['_error_message'] == "Invalid asana api request"


def test_import_asana_list_users(client):
    user = f.UserFactory.create()
    client.login(user)

    url = reverse("importers-asana-list-users")

    with mock.patch('taiga.importers.asana.api.AsanaImporter') as AsanaImporterMock:
        instance = mock.Mock()
        instance.list_users.return_value = [
            {"id": 1, "username": "user1", "full_name": "user1", "detected_user": None},
            {"id": 2, "username": "user2", "full_name": "user2", "detected_user": None}
        ]
        AsanaImporterMock.return_value = instance
        response = client.post(url, content_type="application/json", data=json.dumps({"token": "token", "project": 1}))

    assert response.status_code == 200
    assert response.data[0]["id"] == 1
    assert response.data[1]["id"] == 2


def test_import_asana_list_users_without_project(client):
    user = f.UserFactory.create()
    client.login(user)

    url = reverse("importers-asana-list-users")

    with mock.patch('taiga.importers.asana.api.AsanaImporter') as AsanaImporterMock:
        instance = mock.Mock()
        instance.list_users.return_value = [
            {"id": 1, "username": "user1", "full_name": "user1", "detected_user": None},
            {"id": 2, "username": "user2", "full_name": "user2", "detected_user": None}
        ]
        AsanaImporterMock.return_value = instance
        response = client.post(url, content_type="application/json", data=json.dumps({"token": "token"}))

    assert response.status_code == 400


def test_import_asana_list_users_with_problem_on_request(client):
    user = f.UserFactory.create()
    client.login(user)

    url = reverse("importers-asana-list-users")

    with mock.patch('taiga.importers.asana.importer.AsanaClient') as AsanaClientMock:
        instance = mock.Mock()
        instance.workspaces.find_all.side_effect = exceptions.InvalidRequest()
        AsanaClientMock.oauth.return_value = instance
        response = client.post(url, content_type="application/json", data=json.dumps({"token": "token", "project": 1}))

    assert response.status_code == 400


def test_import_asana_list_projects(client):
    user = f.UserFactory.create()
    client.login(user)

    url = reverse("importers-asana-list-projects")

    with mock.patch('taiga.importers.asana.api.AsanaImporter') as AsanaImporterMock:
        instance = mock.Mock()
        instance.list_projects.return_value = ["project1", "project2"]
        AsanaImporterMock.return_value = instance
        response = client.post(url, content_type="application/json", data=json.dumps({"token": "token"}))

    assert response.status_code == 200
    assert response.data[0] == "project1"
    assert response.data[1] == "project2"


def test_import_asana_list_projects_with_problem_on_request(client):
    user = f.UserFactory.create()
    client.login(user)

    url = reverse("importers-asana-list-projects")

    with mock.patch('taiga.importers.asana.importer.AsanaClient') as AsanaClientMock:
        instance = mock.Mock()
        instance.workspaces.find_all.side_effect = exc.WrongArguments("Invalid Request")
        AsanaClientMock.oauth.return_value = instance
        response = client.post(url, content_type="application/json", data=json.dumps({"token": "token"}))

    assert response.status_code == 400


def test_import_asana_project_without_project_id(client, settings):
    settings.CELERY_ENABLED = True

    user = f.UserFactory.create()
    client.login(user)

    url = reverse("importers-asana-import-project")

    with mock.patch('taiga.importers.asana.tasks.AsanaImporter') as AsanaImporterMock:
        response = client.post(url, content_type="application/json", data=json.dumps({"token": "token"}))

    assert response.status_code == 400


def test_import_asana_project_with_celery_enabled(client, settings):
    settings.CELERY_ENABLED = True

    user = f.UserFactory.create()
    project = f.ProjectFactory.create(slug="async-imported-project")
    client.login(user)

    url = reverse("importers-asana-import-project")

    with mock.patch('taiga.importers.asana.tasks.AsanaImporter') as AsanaImporterMock:
        instance = mock.Mock()
        instance.import_project.return_value = project
        AsanaImporterMock.return_value = instance
        response = client.post(url, content_type="application/json", data=json.dumps({"token": "token", "project": 1}))

    assert response.status_code == 202
    assert "asana_import_id" in response.data


def test_import_asana_project_with_celery_disabled(client, settings):
    settings.CELERY_ENABLED = False

    user = f.UserFactory.create()
    project = f.ProjectFactory.create(slug="imported-project")
    client.login(user)

    url = reverse("importers-asana-import-project")

    with mock.patch('taiga.importers.asana.api.AsanaImporter') as AsanaImporterMock:
        instance = mock.Mock()
        instance.import_project.return_value = project
        AsanaImporterMock.return_value = instance
        response = client.post(url, content_type="application/json", data=json.dumps({"token": "token", "project": 1}))

    assert response.status_code == 200
    assert "slug" in response.data
    assert response.data['slug'] == "imported-project"
