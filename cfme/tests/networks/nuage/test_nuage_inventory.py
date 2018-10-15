# -*- coding: utf-8 -*-
import pytest
from netaddr import IPAddress

from cfme.networks.provider.nuage import NuageProvider
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.provider([NuageProvider], scope="module")]


def test_subnet_details_stats(provider, with_nuage_sandbox):
    """
    This test creates Nuage enterprise and its entities, including subnet.
    Then it validates inventory of created subnet.

    Steps:
        * Deploy some entities outside of MIQ (directly in the provider)
        * Create dictionary with stats that will be validated
        * Find created subnet in database and validate its stats
    """
    sandbox = with_nuage_sandbox
    cidr = '{address}/{netmask}'.format(
        address=sandbox['subnet'].address,
        netmask=IPAddress(sandbox['subnet'].netmask).netmask_bits()
    )
    domain = sandbox['subnet'].parent_object.parent_object
    subnet_stats = {
        'name_value': sandbox['subnet'].name,
        'type_value': 'ManageIQ/Providers/Nuage/Network Manager/Cloud Subnet/L3',
        'cidr_value': cidr,
        'gateway_value': sandbox['subnet'].gateway,
        'network_protocol_value': sandbox['subnet'].ip_type.lower(),
        'network_manager_value': provider.name,
        'cloud_tenant_value': domain.parent_object.name,
        'network_router_value': domain.name,
        'network_ports_num': len(sandbox['subnet'].vports),
        'security_groups_num': sum(len(port.policy_groups) for port in sandbox['subnet'].vports),
    }
    provider.refresh_provider_relationships()
    subnet = object_in_vmdb_with_timeout('nuage_network_subnets', provider, sandbox['subnet'].id)
    subnet.validate_stats(subnet_stats)


def test_network_port_details_stats(provider, with_nuage_sandbox):
    """
    This test creates Nuage enterprise and its entities, including network port.
    Then it validates inventory of created network port.

    Steps:
        * Deploy some entities outside of MIQ (directly in the provider)
        * Create dictionary with stats that will be validated
        * Find created network port in database and validate its stats
    """
    sandbox = with_nuage_sandbox
    floating_ip = provider.mgmt.api.floating_ips.get(
        filter='ID == "{ems_ref}"'.format(ems_ref=sandbox['vm_vport'].associated_floating_ip_id))
    port_stats = {
        'name_value': sandbox['vm_vport'].name,
        'type_value': 'ManageIQ/Providers/Nuage/Network Manager/Network Port/Vm',
        'floating_ip_addresses_value': floating_ip[0].address,
        'cloud_subnets_num': 1,
        'floating_ips_num': len(floating_ip),
        'security_groups_num': len(sandbox['vm_vport'].policy_groups),
    }
    provider.refresh_provider_relationships()
    port = object_in_vmdb_with_timeout('nuage_network_ports', provider, sandbox['vm_vport'].id)
    port.validate_stats(port_stats)


def object_in_vmdb_with_timeout(table, provider, ems_ref):

    def object_from_vmdb():
        logger.info('Looking for {table} with ems_ref {ems_ref} in the VMDB...'.format(
            table=table, ems_ref=ems_ref))
        return getattr(provider.appliance.collections, table).find_by_ems_ref(ems_ref, provider)

    obj, _ = wait_for(
        object_from_vmdb,
        num_sec=60,
        delay=5,
        fail_condition=None
    )
    return obj