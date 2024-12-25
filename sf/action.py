import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.DEBUG)
debug_process = logging.getLogger('process')

class SF:
    def __init__(self, config):
        self.config = config
        # sample entity type
        self.entity_type_map = {
            "APEX CLASS": "ApexClass",
            "APEX TRIGGER": "ApexTrigger",
            "APP": "TabSet",
            "ASSET FILE": "ContentAsset",
            "ASSIGNMENT RULE": "AssignmentRule",
            "AUTH. PROVIDER": "AuthProvider",
            "AUTO-RESPONSE RULE": "AutoResponseRule",
            "COMPACT LAYOUT": "CompactLayout",
            "CUSTOM FIELD": "CustomFieldDefinition",
            "CUSTOM METADATA TYPE": "Custom Metadata Type",
            "CUSTOM OBJECT": "CustomEntityDefinition",
            "CUSTOM PERMISSION": "CustomPermission",
            "CUSTOM REPORT TYPE": "CustomReportType",
            "CUSTOM SETTING": "Custom Settings",
            "DASHBOARD": "Dashboard",
            "EMAIL TEMPLATE": "EmailTemplate",
            "FEED FILTER": "FeedFilterDefinition",
            "FIELD SET": "FieldSet",
            "FLOW DEFINITION": "FlowDefinition",
            "FOLDER": "Folder",
            "GROUP": "Group",
            "LIGHTNING COMPONENT BUNDLE": "AuraDefinitionBundle",
            "LIGHTNING PAGE": "FlexiPage",
            "LIST VIEW": "ListView",
            "NAMED CREDENTIAL": "NamedCredential",
            "PAGE LAYOUT": "Layout",
            "PERMISSION SET": "PermissionSet",
            "QUEUE": "Queues",
            "RECORD TYPE": "RecordType",
            "REPORT": "Report",
            "REPORTING SNAPSHOT": "ReportJob",
            "ROLE": "UserRole",
            "STATIC RESOURCE": "StaticResource",
            "TAB": "CustomTabDefinition",
            "VALIDATION RULE": "ValidationFormula",
            "VISUALFORCE PAGE": "ApexPage",
        }

    async def init(self):
        self.headless = self.config['Browser']['Headless'].lower() == 'true'
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()

    async def wait_for_frame(self, selector, callback=None):
        frame_locator = self.page.frame_locator("[name^='vfFrameId']")

        # wait for the container to be loaded, then process the callback
        action_container = frame_locator.locator(selector).first
        await action_container.wait_for()

        if callback:
            return await callback(frame_locator)

    async def close(self):
        debug_process.debug(f"Close Browser")

        await self.browser.close()
        await self.playwright.stop()

    async def login(self):
        debug_process.debug(f"Run as {self.config['Credential']['Username']}")

        await self.page.goto(self.config['Credential']["LoginUrl"], wait_until="load")
        await self.page.fill("#username", self.config['Credential']["Username"])
        await self.page.fill("#password", self.config['Credential']["Password"])
        await self.page.click("#Login")
        self.host = urlparse(self.page.url).hostname

    async def goto_change_set(self):
        await self.page.goto(
            f"https://{self.host}/one/one.app#/setup/OutboundChangeSet/page?address=%2Fchangemgmt%2FlistOutboundChangeSet.apexp%3FretURL%3D%252Fsetup%252Fhome",
            wait_until="load"
        )
        await self.page.wait_for_selector(".breadcrumbDetail.uiOutputText")

    async def new_change_set(self, name):
        debug_process.debug(f"Adding New Change Set: {name}")

        async def click_new_change_set_button(frame_locator):
            new_button = frame_locator.locator("input[id$='newChangeSet']")
            if new_button:
                await new_button.click()

        async def fill_and_save_change_set(frame_locator, name):
            await frame_locator.locator("input[id$='changeSetName']").fill(name)
            save_button = frame_locator.locator("input[id$='saveChangeSet']").first
            if save_button:
                await save_button.click()

        await self.wait_for_frame("input[id$='newChangeSet']", lambda frame: click_new_change_set_button(frame))
        await self.wait_for_frame("input[id$='changeSetName']", lambda frame: fill_and_save_change_set(frame, name))

    async def add_change_set_components(self, cmps):
        for i, cmp in enumerate(cmps):
            debug_process.debug(f"Process Component ({i+1}/{len(cmps)}): {cmp['entityLabel']}")
            await self.add_change_set_component(cmp)

    async def add_change_set_component(self, cmp):
        debug_process.debug(f"add: {cmp['entityLabel']}...")

        async def click_add_button(frame_locator):
            add_button = frame_locator.locator("input[id$='outboundCs_add']").first
            if add_button:
                await add_button.click()

        async def set_entity_type(frame_locator, cmp):
            entity_button = frame_locator.locator("#entityType")
            if entity_button:
                await entity_button.select_option(self.entity_type_map[cmp["entityType"].upper()])

        async def select_rolodex_index(frame_locator, cmp):
            index = ord(cmp["entityLabel"][0].upper()) - ord("A")
            index_button = frame_locator.locator(f".rolodex .listItem:nth-child({index + 1})").first

            if index_button:
                await index_button.click()

        debug_process.debug(f"click add: {cmp['entityType']}...")
        await self.wait_for_frame("input[id$='outboundCs_add']", lambda frame: click_add_button(frame))

        debug_process.debug(f"set type: {cmp['entityType']}...")
        await self.wait_for_frame("#entityType", lambda frame: set_entity_type(frame, cmp))

        debug_process.debug(f"set rolodex: {cmp['entityLabel'][0].upper()}")
        await self.wait_for_frame(".rolodex", lambda frame: select_rolodex_index(frame, cmp))

        debug_process.debug(f"save: {cmp['entityLabel']}")
        await self.wait_for_frame(".setupBlock .headerRow", lambda frame: self.save_component(frame, cmp))

    async def save_component(self, frame_locator, cmp):
        is_found = False
        while not is_found:
            is_found = await self.find_and_save_component(frame_locator, cmp)


    async def find_and_save_component(self, frame_locator, cmp):
        component = None

        for item in await frame_locator.locator(".setupBlock tr.dataRow").all():
            #TODO Try to find a more accurate way to identify the target cmp
            entity_name = await item.locator("th.dataCell").all_text_contents()
            entity_type = await item.locator("td.dataCell").all_text_contents()

            entity_name = entity_name[0] if len(entity_name) > 0 else None
            entity_type = entity_type[0] if len(entity_type) > 0 else None

            if (entity_name and entity_name == cmp["entityLabel"] and entity_type == cmp["objectLabel"]) or (entity_type is None and entity_name == cmp["entityLabel"]):
                component = item
                break

        if component:
            checkbox = component.locator("input[type='checkbox']").first
            if checkbox:
                await checkbox.click()
            save_button = frame_locator.locator("input[name='save']").first
            if save_button:
                await save_button.click()
            return True
        else:
            more_button = frame_locator.locator(".fewerMore a").first
            if more_button:
                await more_button.click()
            else:
                cancel_button = frame_locator.locator("input[name='cancel']").first
                if cancel_button:
                    await cancel_button.click()
                return True
        return False

