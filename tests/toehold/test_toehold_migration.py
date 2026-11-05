import pytest
from ocp_resources.copy_appliance import CopyAppliance
from ocp_resources.network_map import NetworkMap
from ocp_resources.plan import Plan
from ocp_resources.storage_map import StorageMap
from pytest_testconfig import config as py_config
from timeout_sampler import TimeoutSampler

from utilities.mtv_migration import (
    create_plan_resource,
    execute_migration,
    get_network_migration_map,
    get_storage_migration_map,
)
from utilities.post_migration import check_vms
from utilities.utils import populate_vm_ids

# The controller releases and deletes the CopyAppliance CRs after the migration finishes;
# cleanup is observed rather than assumed to be instantaneous.
COPY_APPLIANCE_CLEANUP_TIMEOUT = 300


@pytest.mark.vsphere
@pytest.mark.toehold
@pytest.mark.tier0
@pytest.mark.incremental
@pytest.mark.parametrize(
    "class_plan_config",
    [
        pytest.param(
            py_config["tests_params"]["test_toehold_cold_migration"],
        )
    ],
    indirect=True,
    ids=["toehold-cold-rhel8"],
)
@pytest.mark.usefixtures("cleanup_migrated_vms", "copy_appliance_template")
class TestToeholdColdMigration:
    """Cold-migrate a Linux VM through a copy appliance (toehold) deployed in vSphere.

    Purpose/Regression:
        Toehold disk transfer (VIRTSTRAT-757): instead of VDDK, MTV clones a copy
        appliance VM from a CopyApplianceTemplate inside vSphere, attaches the
        source disks to it, and exports them over NBD for the destination
        importer. Guards the full chain — template build, appliance check,
        appliance VM lifecycle, and NBD export — against regressions. There is
        no induced failure; the scenario exercises the feature end to end.

    Prerequisites:
        MTV 5.0 with the copy appliance feature (feature_copy_appliance enabled
        on the ForkliftController) and the CDI controller/importer images
        supporting the appliance import path, on an OpenShift destination.
        Register a vSphere source provider whose 'toehold' configuration names
        the datastore (~10GB free per copy appliance VM), a dedicated folder, a
        DHCP-enabled network reachable from the MTV migration network, a
        resource pool, and the base containerdisk image. The provider must not
        configure a VDDK init image (toehold replaces the VDDK transfer path).
        Prepare destination storage and network, and use a disposable RHEL VM
        with guest-agent access.

    Test plan:
        1. Create a CopyApplianceTemplate for the source provider and wait for
           the provider's CopyApplianceChecked condition to be True.
        2. Create a StorageMap for the VM's disks and a NetworkMap for its
           networks. Confirm both are created.
        3. Create a cold Plan for the VM using both maps. Check the Plan's
           Ready condition is True.
        4. Run the migration and check it reaches Succeeded.
        5. Verify the controller released the copy appliances: no CopyAppliance
           CRs remain in the target namespace after the migration.
        6. Validate the migrated VM: power state, guest-agent presence,
           connectivity when powered on, and CPU, memory, network, and storage
           equivalence with the source. After the checks, delete the migrated
           VM; the maps and Plan are removed with the run.

    Expected result:
        The migration succeeds through the copy appliance path and the migrated
        VM matches the source in CPU, memory, disks, and networks, with the
        configured power state and working connectivity, and no CopyAppliance
        CRs are left behind. On failure, inspect the CopyApplianceTemplate
        status (buildPod, phase, stage), the CopyAppliance CR status, the
        controller's copy-appliance logs, the migration CR status for the VM's
        failed step, and the migrated VM's spec and events in the target
        namespace.
    """

    storage_map: StorageMap
    network_map: NetworkMap
    plan_resource: Plan

    def test_create_storagemap(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        destination_provider,
        source_provider_inventory,
        target_namespace,
    ):
        """Create StorageMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.storage_map = get_storage_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=destination_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            vms=vms,
        )
        assert self.storage_map, "StorageMap creation failed"

    def test_create_networkmap(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        destination_provider,
        source_provider_inventory,
        multus_network_name,
    ):
        """Create NetworkMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.network_map = get_network_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=destination_provider,
            source_provider_inventory=source_provider_inventory,
            multus_network_name=multus_network_name,
            vms=vms,
        )
        assert self.network_map, "NetworkMap creation failed"

    def test_create_plan(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        destination_provider,
        target_namespace,
        source_provider_inventory,
    ):
        """Create MTV Plan CR resource."""
        populate_vm_ids(prepared_plan, source_provider_inventory)

        self.__class__.plan_resource = create_plan_resource(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=destination_provider,
            storage_map=self.storage_map,
            network_map=self.network_map,
            virtual_machines_list=prepared_plan["virtual_machines"],
            target_namespace=target_namespace,
            warm_migration=prepared_plan.get("warm_migration", False),
        )
        assert self.plan_resource, "Plan creation failed"

    def test_migrate_vms(
        self,
        fixture_store,
        ocp_admin_client,
        target_namespace,
    ):
        """Execute migration."""
        execute_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            plan=self.plan_resource,
            target_namespace=target_namespace,
        )

    def test_verify_copy_appliance_cleanup(
        self,
        ocp_admin_client,
        target_namespace,
    ):
        """Verify CopyAppliance CRs are released after the migration."""
        for copy_appliances in TimeoutSampler(
            wait_timeout=COPY_APPLIANCE_CLEANUP_TIMEOUT,
            sleep=30,
            func=lambda: list(CopyAppliance.get(client=ocp_admin_client, namespace=target_namespace)),
        ):
            if not copy_appliances:
                break

    def test_check_vms(
        self,
        prepared_plan,
        source_provider,
        destination_provider,
        source_provider_data,
        target_namespace,
        source_vms_namespace,
        source_provider_inventory,
        vm_ssh_connections,
    ):
        """Validate migrated VMs."""
        check_vms(
            plan=prepared_plan,
            source_provider=source_provider,
            destination_provider=destination_provider,
            network_map_resource=self.network_map,
            storage_map_resource=self.storage_map,
            source_provider_data=source_provider_data,
            source_vms_namespace=source_vms_namespace,
            source_provider_inventory=source_provider_inventory,
            vm_ssh_connections=vm_ssh_connections,
        )
