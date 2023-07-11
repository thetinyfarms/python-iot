"""
"Copyright 2023 ClearBlade Inc."

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
https://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
Copyright 2018 Google LLC
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
https://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
Copyright 2023 ClearBlade Inc.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
https://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
Copyright 2018 Google LLC
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
https://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os

from .config import ClearBladeConfig
from .http_client import AsyncClient, SyncClient
from .utils import find_project_region_registry_from_parent


class ClearBladeConfigManager:
    def __init__(self) -> None:
        self._admin_config: ClearBladeConfig = None
        self._regional_config: ClearBladeConfig = None
        self._registry_name: str = None
        self._region_name: str = None

    def _set_admin_clearblade_config(self):
        if self._admin_config:
            return

        service_account_credentials = os.environ.get("CLEARBLADE_CONFIGURATION")
        service_account_data = None
        
        if service_account_credentials is None:
            raise Exception('CLEARBLADE_CONFIGURATION environment variable is not set')
        
        if os.path.isfile(service_account_credentials):
            #parse the file and get all te required details.
            with open(service_account_credentials, mode='r') as service_account_file:
                service_account_data = json.load(service_account_file)
        else:
            #parse string as json config
            service_account_data = json.loads(service_account_credentials)

        if service_account_data is None:
            raise Exception('ClearBlade Service account file is empty')

        system_key = service_account_data['systemKey']
        auth_token = service_account_data['token']
        api_url = service_account_data['url']
        project = service_account_data['project']

        self._admin_config = ClearBladeConfig(system_key=system_key, auth_token=auth_token,
                                                 api_url=api_url, project=project)

    def _create_regional_config_from_env(self, systemKey:str = None, serviceAccountToken:str = None, url:str = None, region:str = None)-> ClearBladeConfig :
        return ClearBladeConfig(system_key=systemKey, auth_token=serviceAccountToken, api_url=url,
                                region=region, project=self._admin_config.project)

    
    def _create_regional_config(self, regional_json: json = None)-> ClearBladeConfig :
        system_key = regional_json['systemKey']
        auth_token = regional_json['serviceAccountToken']
        api_url = regional_json['url']
        region = regional_json['region']

        return ClearBladeConfig(system_key=system_key, auth_token=auth_token, api_url=api_url,
                                region=region, project=self._admin_config.project)

    def _set_regional_config(self, region:str = None, registry:str = None):
        self._set_admin_clearblade_config()

        if not region:
            region = self.region_name

        if not registry:
            registry = self.registry_name

        if not region or not registry:
            raise Exception("Either location or registry name is not provided")
        
        system_key = os.environ.get("REGISTRY_SYSKEY")
        registry_token = os.environ.get("REGISTRY_TOKEN")
        url = os.environ.get("REGISTRY_URL")
        if (system_key and registry_token and url) :
            self._regional_config = self._create_regional_config_from_env(systemKey=system_key , serviceAccountToken = registry_token, url = url, region = region)
        else :
            request_body = {'region':region,'registry':registry, 'project':self._admin_config.project}
            sync_client = SyncClient(clearblade_config=self._admin_config)
            response = sync_client.post(api_name="getRegistryCredentials", is_webhook_folder=False,
                                        request_body=request_body)
            if response.status_code != 200:
                raise Exception(
                    f"\n\nRegistry Information not found! Please check if the given registry exists\nProject: {self._admin_config.project}\nRegistry: {registry}\nRegion: {region}"
                    )
            response_json = response.json()
            response_json['region'] = region
            self._regional_config = self._create_regional_config(regional_json=response_json) 
            

    async def _set_regional_config_async(self, region:str = None, registry:str = None):

        self._set_admin_clearblade_config()

        if not region:
            region = self._region_name

        if not registry:
            registry = self.registry_name
        system_key = os.environ.get("REGISTRY_SYSKEY")
        registry_token = os.environ.get("REGISTRY_TOKEN")
        url = os.environ.get("REGISTRY_URL")
        if (system_key and registry_token) :
            self._regional_config = self._create_regional_config_from_env(systemKey=system_key , serviceAccountToken = registry_token, url = url, region = region)
        else :            
            async_client = AsyncClient(clearblade_config=self._admin_config)
            request_body = {'region':region,'registry':registry, 'project':self._admin_config.project}
            response = await async_client.post(api_name="getRegistryCredentials",
                                            is_webhook_folder=False,
                                            request_body=request_body)

            if response.status_code != 200:
                raise Exception(
                    f"\n\nRegistry Information not found! Please check if the given registry exists\nProject: {self._admin_config.project}\nRegistry: {registry}\nRegion: {region}"
                    )
            response_json = response.json()
            response_json['region'] = region
            self._regional_config = self._create_regional_config(regional_json=response_json)


    @property
    def admin_config(self):
        if not self._admin_config:
            self._set_admin_clearblade_config()

        return self._admin_config

    def regional_config(self, parent: str):
        if not self._regional_config:
            project = find_project_region_registry_from_parent(parent)
            self._set_regional_config(region=project['location'], registry=project['registry'])

        return self._regional_config

    async def regional_config_async(self, parent: str):
        if not self._regional_config:
            project = find_project_region_registry_from_parent(parent)
            await self._set_regional_config_async(region=project['location'], registry=project['registry'])

        return self._regional_config

    @property
    def registry_name(self):
        return self._registry_name

    @property
    def region_name(self):
        return self._region_name

    @registry_name.setter
    def registry_name(self, registry_name):
        self._registry_name = registry_name

    @region_name.setter
    def region_name(self, region_name):
        self._region_name = region_name
