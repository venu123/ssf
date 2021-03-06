# -*- coding: utf-8 -*-

"""
    Incident Reporting System - Controllers
"""

module = request.controller
resourcename = request.function

if not deployment_settings.has_module(module):
    raise HTTP(404, body="Module disabled: %s" % module)

# -----------------------------------------------------------------------------
def index():

    """ Custom View """

    module_name = deployment_settings.modules[module].name_nice
    response.title = module_name
    return dict(module_name=module_name)


# -----------------------------------------------------------------------------
@auth.s3_requires_membership(1)
def icategory():

    """
        Incident Categories, RESTful controller
        Note: This just defines which categories are visible to end-users
        The full list of hard-coded categories are visible to admins & should remain unchanged for sync
    """

    output = s3_rest_controller()
    return output

# -----------------------------------------------------------------------------
def ireport():

    """ Incident Reports, RESTful controller """

    tablename = "%s_%s" % (module, resourcename)
    table = s3db[tablename]

    if "open" in request.get_vars:
        # Filter out Reports that are closed or Expired
        s3.crud_strings[tablename].title_list = T("Open Incidents")
        response.s3.filter = (table.closed == False) & \
                             ((table.expiry == None) | \
                              (table.expiry > request.utcnow))

    # Non-Editors should only see a limited set of options
    if not s3_has_role(EDITOR):
        irs_incident_type_opts = response.s3.irs_incident_type_opts
        ctable = s3db.irs_icategory
        allowed_opts = [irs_incident_type_opts.get(opt.code, opt.code) for opt in db().select(ctable.code)]
        allowed_opts.sort()
        table.category.requires = IS_NULL_OR(IS_IN_SET(allowed_opts))

    # Pre-processor
    def prep(r):
        table = r.table
        if r.method == "ushahidi":
            auth.settings.on_failed_authorization = r.url(method="", vars=None)
            # Allow the 'XX' levels
            s3db.gis_location.level.requires = IS_NULL_OR(IS_IN_SET(
                                                gis.get_all_current_levels()))
        elif r.interactive or r.representation == "aadata":
            if r.method == "update":
                table.dispatch.writable = True
                table.verified.writable = True
                table.closed.writable = True
            if r.component:
                if r.component_name == "image":
                    itable = s3db.doc_image
                    itable.date.default = r.record.datetime.date()
                    itable.location_id.default = r.record.location_id
                    itable.location_id.readable = itable.location_id.writable = False
                    itable.organisation_id.readable = itable.organisation_id.writable = False
                    #itable.url.readable = itable.url.writable = False
                    itable.person_id.readable = itable.person_id.writable = False
                elif r.component_name == "document":
                    dtable = s3db.doc_document
                    dtable.date.default = r.record.datetime.date()
                    dtable.location_id.default = r.record.location_id
                    dtable.location_id.readable = dtable.location_id.writable = False
                    dtable.organisation_id.readable = dtable.organisation_id.writable = False
                    #dtable.url.readable = dtable.url.writable = False
                    dtable.person_id.readable = dtable.person_id.writable = False
                elif r.component_name == "human_resource":
                    s3.crud.submit_button = T("Assign")
                    s3.crud_strings["irs_ireport_human_resource"] = Storage(
                        title_create = T("Assign Human Resource"),
                        title_display = T("Human Resource Details"),
                        title_list = T("List Assigned Human Resources"),
                        title_update = T("Edit Human Resource"),
                        title_search = T("Search Assigned Human Resources"),
                        subtitle_create = T("Assign New Human Resource"),
                        subtitle_list = T("Human Resource Assignments"),
                        label_list_button = T("List Assigned Human Resources"),
                        label_create_button = T("Assign Human Resource"),
                        label_delete_button = T("Remove Human Resource from this incident"),
                        msg_record_created = T("Human Resource assigned"),
                        msg_record_modified = T("Human Resource Assignment updated"),
                        msg_record_deleted = T("Human Resource unassigned"),
                        msg_list_empty = T("No Human Resources currently assigned to this incident"))
                elif r.component_name == "vehicle":
                    s3.crud.submit_button = T("Assign")
                    s3.crud_strings["irs_ireport_vehicle"] = Storage(
                        title_create = T("Assign Vehicle"),
                        title_display = T("Vehicle Details"),
                        title_list = T("List Assigned Vehicles"),
                        title_update = T("Edit Vehicle Assignment"),
                        title_search = T("Search Vehicle Assignments"),
                        subtitle_create = T("Add New Vehicle Assignment"),
                        subtitle_list = T("Vehicle Assignments"),
                        label_list_button = T("List Vehicle Assignments"),
                        label_create_button = T("Add Vehicle Assignment"),
                        label_delete_button = T("Remove Vehicle from this incident"),
                        msg_record_created = T("Vehicle assigned"),
                        msg_record_modified = T("Vehicle Assignment updated"),
                        msg_record_deleted = T("Vehicle unassigned"),
                        msg_list_empty = T("No Vehicles currently assigned to this incident"))

        return True
    response.s3.prep = prep

    # Post-processor
    def user_postp(r, output):
        if not r.component:
            s3_action_buttons(r, deletable=False)
            # if deployment_settings.has_module("assess"):
                # response.s3.actions.append({"url" : URL(c="assess", f="basic_assess",
                                                        # vars = {"ireport_id":"[id]"}),
                                            # "_class" : "action-btn",
                                            # "label" : "Assess"})
        return output
    response.s3.postp = user_postp

    output = s3_rest_controller(rheader=response.s3.irs_rheader,
                                interactive_report = True)

    # @ToDo: Add 'Dispatch' button to send OpenGeoSMS
    #try:
    #    delete_btn = output["delete_btn"]
    #except:
    #    delete_btn = ""
    #buttons = DIV(delete_btn)
    #output.update(delete_btn=buttons)

    return output

# END =========================================================================
