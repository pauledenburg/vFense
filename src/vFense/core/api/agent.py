import simplejson as json

import logging
import logging.config
from vFense import VFENSE_LOGGING_CONFIG

from vFense.core.api.base import BaseHandler
from vFense.core.permissions._constants import Permissions
from vFense.core.permissions.permissions import (
    verify_permission_for_user, return_results_for_permissions
)

from vFense.core._constants import CommonKeys
from vFense.core.permissions.decorators import check_permissions
from vFense.core.operations.decorators import log_operation
from vFense.core.operations._admin_constants import AdminActions
from vFense.core.operations._constants import vFenseObjects
from vFense.core.agent._db_model import AgentKeys
from vFense.core.user._db_model import UserKeys
from vFense.core.user.manager import UserManager
from vFense.core.user.search.search import RetrieveUsers
from vFense.core.agent.search.search import RetrieveAgents
from vFense.core.agent.manager import AgentManager
from vFense.core.queue.uris import get_result_uris
from vFense.errorz.error_messages import GenericResults

from vFense.plugins.patching.operations.store_operations import (
    StorePatchingOperation
)
from vFense.core.agent.operations.store_agent_operations import (
    StoreAgentOperations
)
from vFense.core.agent.agents import (
    get_supported_os_codes, get_supported_os_strings, get_production_levels
)

from vFense.core.operations._db_model import *
from vFense.core.decorators import (
    authenticated_request, convert_json_to_arguments, results_message
)
from vFense.errorz._constants import ApiResultKeys
from vFense.errorz.status_codes import (
    UserCodes, UserFailureCodes, GenericCodes,
    GenericFailureCodes
)
from vFense.core.user.search.search import RetrieveUsers

logging.config.fileConfig(VFENSE_LOGGING_CONFIG)
logger = logging.getLogger('rvapi')


class AgentResultURIs(BaseHandler):
    @authenticated_request
    def get(self, agent_id):
        username = self.get_current_user()
        uri = self.request.uri
        method = self.request.method
        try:
            results = get_result_uris(agent_id, username, uri, method)
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            status = (
                GenericResults(
                    username, uri, method
                ).something_broke('uris', 'refresh_response_uris', e)
            )
            logger.exception(e)
            self.write(json.dumps(status, indent=4))


class FetchValidProductionLevels(BaseHandler):
    @authenticated_request
    def get(self):
        username = self.get_current_user().encode('utf-8')
        view_name = (
            UserManager(username).get_attribute(UserKeys.CurrentView)
        )
        uri = self.request.uri
        method = self.request.method
        try:
            data = get_production_levels(view_name)
            results = (
                GenericResults(
                    username, uri, method
                ).information_retrieved(data, len(data))
            )
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    username, uri, method
                ).something_broke('Get OS Codes', 'Agent', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))


class FetchSupportedOperatingSystems(BaseHandler):
    @authenticated_request
    def get(self):
        username = self.get_current_user().encode('utf-8')
        view_name = (
            UserManager(username).get_attribute(UserKeys.CurrentView)
        )
        uri = self.request.uri
        method = self.request.method
        try:
            os_code = self.get_argument('os_code', None)
            os_string = self.get_argument('os_string', None)
            if not os_code and not os_string or os_code and not os_string:
                data = get_supported_os_codes()

            elif os_string:
                data = get_supported_os_strings(view_name)

            results = (
                GenericResults(
                    username, uri, method
                ).information_retrieved(data, len(data))
            )
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    username, uri, method
                ).something_broke('Get OS Codes', 'Agent', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))


class AgentsHandler(BaseHandler):
    @authenticated_request
    @check_permissions(Permissions.READ)
    def get(self):
        active_user = self.get_current_user()
        uri = self.request.uri
        method = self.request.method
        user = UserManager(active_user)
        active_view = user.get_attribute(UserKeys.CurrentView)
        try:
            count = int(self.get_argument('count', 30))
            offset = int(self.get_argument('offset', 0))
            query = self.get_argument('query', None)
            fkey = self.get_argument('filter_key', None)
            fval = self.get_argument('filter_val', None)
            ip = self.get_argument('ip', None)
            mac = self.get_argument('mac', None)
            sort = self.get_argument('sort', 'asc')
            sort_by = self.get_argument('sort_by', AgentKeys.ComputerName)

            search = (
                RetrieveAgents(active_view, count, offset, sort, sort_by)
            )
            if not ip and not mac and not query and not fkey and not fval:
                results = self.get_all_agents(search)

            elif query and not ip and not mac and not fkey and not fval:
                results = self.get_all_agents_by_name(search, query)

            elif ip and not mac and not query and not fkey and not fval:
                results = self.get_all_agents_by_ip(search, ip)

            elif mac and not ip and not query and not fkey and not fval:
                results = self.get_all_agents_by_mac(search, mac)

            elif fkey and fval and not ip and not mac and not query:
                results = self.get_all_agents_by_key_val(search, fkey, fval)

            elif query and fkey and fval and not mac and not ip:
                results = (
                    self.get_all_agents_by_key_val_and_query(
                        search, fkey, fval, query
                    )
                )

            elif ip and fkey and fval and not mac and not query:
                results = (
                    self.get_all_agents_by_ip_and_filter(
                        search, ip, fkey, fval
                    )
                )

            elif mac and fkey and fval and not ip and not query:
                results = (
                    self.get_all_agents_by_mac_and_filter(
                        search, mac, fkey, fval
                    )
                )

            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    active_user, uri, method
                ).something_broke('Agents Api', 'agent', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

    @results_message
    def get_all_agents(self, search):
        results = search.all()
        return results

    @results_message
    def get_all_agents_by_name(self, search, name):
        results = search.by_name(name)
        return results

    @results_message
    def get_all_agents_by_ip(self, search, ip):
        results = search.by_ip(ip)
        return results

    @results_message
    def get_all_agents_by_mac(self, search, mac):
        results = search.by_mac(mac)
        return results

    @results_message
    def get_all_agents_by_key_val(self, search, key, val):
        results = search.by_key_and_val(key, val)
        return results

    @results_message
    def get_all_agents_by_key_val_and_query(self, search, key, val, query):
        results = search.by_key_and_val(key, val, query)
        return results

    @results_message
    def get_all_agents_by_ip_and_filter(self, search, ip, key, val):
        results = search.by_ip_and_filter(ip, key, val)
        return results

    @results_message
    def get_all_agents_by_mac_and_filter(self, search, mac, key, val):
        results = search.by_mac_and_filter(mac, key, val)
        return results

    @authenticated_request
    @convert_json_to_arguments
    @check_permissions(Permissions.ADMINISTRATOR)
    def put(self):
        username = self.get_current_user()
        view_name = (
            UserManager(username).get_attribute(UserKeys.CurrentView)
        )
        uri = self.request.uri
        method = self.request.method
        try:
            agent_ids = self.arguments.get('agent_ids')
            new_view = self.arguments.get('view_name')
            if not isinstance(agent_ids, list):
                agent_ids = agent_ids.split()
            agentids_moved =[]
            agentids_not_moved =[]
            for agent_id in agent_ids:
                agent = AgentManager(agent_id, view_name=view_name)
                results = agent.change_view(new_view, uri, method)
                if results['http_status'] == 200:
                    agentids_moved.append(agent_id)
                else:
                    agentids_not_moved.append(agent_id)
            results['data'] = {
                'agentids_moved': agentids_moved,
                'agentids_not_moved': agentids_not_moved
            }
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    username, uri, method
                ).something_broke('agent_ids', 'delete agentids', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))


    @authenticated_request
    @convert_json_to_arguments
    @check_permissions(Permissions.ADMINISTRATOR)
    def delete(self):
        username = self.get_current_user()
        view_name = (
            UserManager(username).get_attribute(UserKeys.CurrentView)
        )
        uri = self.request.uri
        method = self.request.method
        try:
            agent_ids = self.arguments.get('agent_ids')
            if not isinstance(agent_ids, list):
                agent_ids = agent_ids.split()
            agentids_deleted =[]
            agentids_not_deleted =[]
            for agent_id in agent_ids:
                agent = AgentManager(agent_id, view_name=view_name)
                results = agent.delete_agent(uri, method)
                if results['http_status'] == 200:
                    delete_oper = (
                        StorePatchingOperation(
                            username, view_name, uri, method
                        )
                    )
                    delete_oper.uninstall_agent(agent_id)
                    agentids_deleted.append(agent_id)
                else:
                    agentids_not_deleted.append(agent_id)
            results['data'] = {
                'agentids_deleted': agentids_deleted,
                'agentids_not_deleted': agentids_not_deleted
            }
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    username, uri, method
                ).something_broke('agent_ids', 'delete agentids', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))


class AgentHandler(BaseHandler):
    @authenticated_request
    def get(self, agent_id):
        username = self.get_current_user()
        view_name = (
            UserManager(username).get_attribute(UserKeys.CurrentView)
        )
        uri = self.request.uri
        method = self.request.method
        try:
            agent = AgentManager(agent_id, view_name=view_name)
            results = agent.get_data(uri=uri, method=method)
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    username, uri, method
                ).something_broke(agent_id, 'get agent_info', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

    @authenticated_request
    @convert_json_to_arguments
    @check_permissions(Permissions.ADMINISTRATOR)
    def put(self, agent_id):
        username = self.get_current_user()
        view_name = (
            UserManager(username).get_attribute(UserKeys.CurrentView)
        )
        uri = self.request.uri
        method = self.request.method
        try:
            displayname = self.arguments.get('display_name', None)
            hostname = self.arguments.get('hostname', None)
            prod_level = self.arguments.get('production_level', None)
            new_view = self.arguments.get('view_name', None)
            agent = AgentManager(agent_id, view_name=view_name)

            if (displayname and not hostname and not
                    prod_level and not new_view):
                results = agent.displayname_changer(displayname, uri, method)

            elif (hostname and not prod_level and not displayname
                    and not new_view):
                results = agent.hostname_changer(hostname, uri, method)

            elif (prod_level and not hostname and not displayname
                    and not new_view):
                results = agent.production_state_changer(prod_level, uri, method)

            elif prod_level and hostname and displayname and not new_view:
                agent_data = {
                    'host_name': hostname,
                    'production_level': prod_level,
                    'display_name': displayname
                }
                results = agent.update_fields(agent_data, uri, method)

            elif (new_view and not prod_level and not hostname
                and not displayname):
                results = agent.change_view(new_view, uri, method)

            else:
                results = (
                    GenericResults(
                        username, uri, method
                    ).incorrect_arguments()
                )

            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    username, uri, method
                ).something_broke(agent_id, 'modify agent', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

    @authenticated_request
    @check_permissions(Permissions.ADMINISTRATOR)
    def delete(self, agent_id):
        username = self.get_current_user()
        view_name = (
            UserManager(username).get_attribute(UserKeys.CurrentView)
        )
        uri = self.request.uri
        method = self.request.method
        try:
            agent = AgentManager(agent_id, view_name=view_name)
            delete_oper = StorePatchingOperation(username, view_name, uri, method)
            delete_oper.uninstall_agent(agent_id)
            results = agent.delete_agent(uri, method)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    username, uri, method
                ).something_broke(agent_id, 'delete agent', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

    @authenticated_request
    @convert_json_to_arguments
    def post(self, agent_id):
        username = self.get_current_user()
        view_name = (
            UserManager(username).get_attribute(UserKeys.CurrentView)
        )
        uri = self.request.uri
        method = self.request.method
        try:
            reboot = self.arguments.get('reboot', None)
            shutdown = self.arguments.get('shutdown', None)
            apps_refresh = self.arguments.get('apps_refresh', None)
            operation = (
                StoreAgentOperations(
                    username, view_name, uri, method
                )
            )
            if reboot:
                granted, status_code = (
                    verify_permission_for_user(
                        username, Permissions.REBOOT
                    )
                )
                if granted:
                    results = (
                        operation.reboot([agent_id])
                    )

                else:
                    results = (
                        return_results_for_permissions(
                            username, granted, status_code,
                            Permissions.REBOOT, uri, method
                        )
                    )

            elif shutdown:
                granted, status_code = (
                    verify_permission_for_user(
                        username, Permissions.SHUTDOWN
                    )
                )
                if granted:
                    results = (
                        operation.shutdown([agent_id])
                    )

                else:
                    results = (
                        return_results_for_permissions(
                            username, granted, status_code,
                            Permissions.SHUTDOWN, uri, method
                        )
                    )

            elif apps_refresh:
                operation = (
                    StorePatchingOperation(
                        username, view_name, uri, method
                    )
                )
                results = (
                    operation.apps_refresh([agent_id])
                )

            else:
                results = (
                    GenericResults(
                        username, uri, method
                    ).incorrect_arguments()
                )

            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

        except Exception as e:
            results = (
                GenericResults(
                    username, uri, method
                ).something_broke(agent_id, '', e)
            )
            logger.exception(e)
            self.set_status(results['http_status'])
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(results, indent=4))

'''
class NodeWolHandler(BaseHandler):
    @authenticated_request
    def post(self):
        username = self.get_current_user()
        session = self.application.session
        session = validate_session(session)
        list_of_nodes = self.get_arguments('nodes')
        if (list_of_nodes) >0:
            result = wake_up_nodes(session,
                    node_list=list_of_nodes
                    )
        else:
            result = {
                'pass': False,
                'message': 'Incorrect argument passed. %s' %
                    ('Arguments needed are: nodeid')
                }
        self.session.close()
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(result, indent=4))
'''
