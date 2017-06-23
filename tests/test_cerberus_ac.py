# -*- coding: utf-8 -*-

"""Main test script."""

from django.test import TestCase, override_settings

import pytest
from django_fake_model import models as f

from cerberus_ac.apps import AppSettings
from cerberus_ac.models import (
    AccessHistory, PrivilegeHistory, Role, RoleHierarchy, RoleMixin,
    RolePrivilege)
from cerberus_ac.utils import get_resource_id, get_resource_type


class FakeUser(f.FakeModel, RoleMixin):
    """Fake user model."""


class FakeGroup(f.FakeModel, RoleMixin):
    """Fake group model."""


class FakeResource(f.FakeModel):
    """Fake resource model."""


@FakeUser.fake_me
@FakeGroup.fake_me
@FakeResource.fake_me
class MainTestCase(TestCase):
    """Main Django test case."""

    def setUp(self):
        """Setup method."""
        self.set_users()
        self.set_groups()
        self.set_roles()
        self.set_resources()
        self.set_role_hierarchy()
        self.set_role_privileges()

    def set_users(self):
        """Add users to self."""
        self.users = [FakeUser.objects.create() for _ in range(3)]

    def set_groups(self):
        """Add groups to self."""
        self.groups = [FakeGroup.objects.create() for _ in range(3)]

    def set_roles(self):
        """Add custom roles to self."""
        self.roles = [
            Role.objects.create(type='security'),
            Role.objects.create(type='audit', rid=15),
            Role.objects.create(type='data')
        ]

    def set_resources(self):
        """Add resources to self."""
        self.resources = [FakeResource.objects.create() for _ in range(3)]

    def test_appsettings_instance(self):
        """Instantiate an AppSettings instance."""
        appsettings = AppSettings()
        assert appsettings.mapping

    @override_settings(CERBERUS_DEFAULT_RESPONSE='a',
                       CERBERUS_SKIP_IMPLICIT=1,
                       CERBERUS_LOG_ACCESS=[],
                       CERBERUS_LOG_PRIVILEGES={},
                       CERBERUS_LOG_HIERARCHY=None,
                       CERBERUS_ROLES_LIST={},
                       CERBERUS_RESOURCES_LIST=[1, 2])
    def test_wrong_settings_trigger_exception(self):
        """Check that settings with wrong values trigger exceptions."""
        with pytest.raises(ValueError):
            AppSettings.default_response.check()
        with pytest.raises(ValueError):
            AppSettings.skip_implicit.check()
        with pytest.raises(ValueError):
            AppSettings.log_access.check()
        with pytest.raises(ValueError):
            AppSettings.log_privileges.check()
        with pytest.raises(ValueError):
            AppSettings.log_hierarchy.check()

    def test_import_classes(self):
        """Test classes imported correctly."""
        assert set(AppSettings.mapping.get().role_classes()) == {Role, FakeUser, FakeGroup}  # noqa

    def test_getting_resource_type_and_id(self):
        """Test get_resource_type and get_resource_id methods."""
        class NoDatabaseResource(object):
            """Just an empty Python class."""

        nodb_resource_1 = NoDatabaseResource()
        nodb_resource_1.resource_id = 30
        nodb_resource_1.resource_type = 'no_db'
        nodb_resource_2 = NoDatabaseResource()

        class NoDatabaseResource2(object):
            """Fake resource class without model."""

            def resource_type(self):
                return 'user_data'

            def resource_id(self):
                return None

        nodb_resource_3 = NoDatabaseResource2()

        assert get_resource_type(nodb_resource_1) == 'no_db'
        assert get_resource_id(nodb_resource_1) == 30
        assert get_resource_type(nodb_resource_2) == 'NoDatabaseResource'
        assert get_resource_id(nodb_resource_2) is None
        assert get_resource_type(nodb_resource_3) == 'user_data'
        assert get_resource_id(nodb_resource_3) is None
        assert get_resource_type(object) == 'object'
        assert get_resource_type(1) == 'int'

    def set_role_hierarchy(self):
        """Set a role hierarchy."""
        self.users[0].take_role(self.groups[0])
        self.users[0].take_role(self.groups[1])
        self.groups[1].convey_to(self.users[1])
        self.roles[0].convey_to(self.users[0])
        self.roles[1].convey_to(self.users[1])
        self.roles[2].convey_to(self.users[2])
        self.roles[2].take_role(self.groups[2])

    def test_role_hierarchy(self):
        """Role hierarchy test method."""
        assert self.users[0].has_role(self.groups[0])
        assert self.users[0].has_role(self.groups[1])
        assert not self.users[0].has_role(self.groups[2])
        assert not self.groups[2].conveys_to(self.groups[1])
        assert set(self.groups[1].heirs()) == {
            self.users[0], self.users[1]}
        assert self.roles[0].conveys_to(self.users[0])
        assert self.roles[1].conveys_to(self.users[1])
        assert self.roles[2].conveys_to(self.users[2])
        assert set(self.users[0].conveyors()) == {
            self.groups[0], self.groups[1], self.roles[0]}
        assert set(
            self.users[2].conveyors(search=RoleHierarchy.DEPTH_FIRST)) == set(
            self.users[2].conveyors(search=RoleHierarchy.BREADTH_FIRST))
        assert set(
            self.groups[2].heirs(search=RoleHierarchy.DEPTH_FIRST)) == set(
            self.groups[2].heirs(search=RoleHierarchy.BREADTH_FIRST))

    def test_role_hierarchy_history(self):
        """Test role hierarchy history."""
        pass  # TODO: need implementation of HierarchyHistory first

    def set_role_privileges(self):
        """Set some role privileges."""
        RolePrivilege.allow('FakeUser', '1', 'do stuff on', 'FakeResource', '1')
        RolePrivilege.allow('FakeUser', '2', 'do stuff on', 'FakeResource', '2')
        RolePrivilege.allow('FakeUser', '3', 'do stuff on', 'FakeResource', '3')
        RolePrivilege.deny('FakeUser', '1', 'do stuff on', 'FakeResource', '2')
        RolePrivilege.deny('FakeUser', '2', 'do stuff on', 'FakeResource', '3')
        RolePrivilege.deny('FakeUser', '3', 'do stuff on', 'FakeResource', '1')
        RolePrivilege.allow('FakeGroup', '3', 'read', 'FakeResource', '3')
        RolePrivilege.allow('FakeGroup', '3', 'delete', 'FakeResource', '3')
        RolePrivilege.forget('FakeGroup', '3', 'delete', 'FakeResource', '3')
        RolePrivilege.forget('FakeGroup', '3', 'create', 'FakeResource', '3')
        RolePrivilege.allow('data', '', 'update', 'FakeResource', '3')

    def test_role_privileges(self):
        """Test the roles privileges."""
        # test direct explicit permission
        assert self.users[0].can('do stuff on', self.resources[0])
        assert self.users[1].can('do stuff on', self.resources[1])
        assert self.users[2].can('do stuff on', self.resources[2])
        assert not self.users[0].can('do stuff on', self.resources[1])
        assert not self.users[1].can('do stuff on', self.resources[2])
        assert not self.users[2].can('do stuff on', self.resources[0])
        assert not self.users[0].can('do stuff on', self.resources[2])
        assert not self.users[1].can('do stuff on', self.resources[0])
        assert not self.users[2].can('do stuff on', self.resources[1])
        # test indirect-1 explicit permission
        assert self.users[2].can('update', self.resources[2])
        # test indirect-2 explicit permission
        assert self.users[2].can('read', self.resources[2])
        # test direct overridden indirect-1 permission
        RolePrivilege.deny('FakeUser', '3', 'update', 'FakeResource', '3')
        assert not self.users[2].can('update', self.resources[2])
        # test direct overridden indirect-2 permission
        RolePrivilege.deny('data', '', 'read', 'FakeResource', '3')
        assert not self.users[2].can('read', self.resources[2])
        # test clashing same-level permissions

    def test_role_privileges_history(self):
        """Test role privileges history."""
        for i in (1, 2, 3):
            assert RolePrivilege.objects.get(
                role_type='FakeUser',
                role_id=i,
                access_type='do stuff on',
                authorized=True,
                resource_type='FakeResource',
                resource_id=i)
            j = {1: 2, 2: 3, 3: 1}.get(i)
            assert RolePrivilege.objects.get(
                role_type='FakeUser',
                role_id=i,
                access_type='do stuff on',
                authorized=False,
                resource_type='FakeResource',
                resource_id=j)

    def test_str_method(self):
        """Test printing methods of models."""
        self.test_role_privileges()
        for queryset in [
            Role.objects.all(),
            RolePrivilege.objects.all(),
            RoleHierarchy.objects.all(),
            AccessHistory.objects.all(),
            PrivilegeHistory.objects.all(),
            # HierarchyHistory.objects.all()[0],
        ]:
            for obj in queryset:
                print(obj)

    def tearDown(self):
        """Tear down method."""
        pass
