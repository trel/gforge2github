#!/usr/bin/env python

##############################################################
#
#  gforge2github.py
#  GForge 2 GitHub
#
#  Terrell Russell
#  terrellrussell@gmail.com
#
##############################################################

# credentials
import config
import logging
from datetime import datetime
import sys
sys.path.append( "PyGithub" )
from github import Github
from github import GithubException

logging.basicConfig(level = logging.INFO)
GITHUB_SPARE_REQUESTS = 50

def log_github_rate_info():
    logging.info( 'GitHub Rate limit (remaining/total): %s',repr(github.rate_limiting))

def github_label(name, color = "FFFFFF"):

    """ Returns the Github label with the given name, creating it if necessary. """

    try: return github_label_cache[name]
    except KeyError:
        try: return github_label_cache.setdefault(name, github_repo.get_label(name))
        except GithubException:
            return github_label_cache.setdefault(name, github_repo.create_label(name, color))

def check_user_mapping():
    errorflag = 0

    # check the local mapping from config.py
    localnotfound = set()
    for k, u in gforge_users.iteritems():
        try:
            found = github_username_by_gforge_username(u['unix_name'])
            # print "found [%s] as [%s]" % (u['unix_name'], found)
        except:
            # print "[%s] not found" % u['unix_name']
            localnotfound.add(u['unix_name'])
    if len(localnotfound) > 0:
        errorflag = 1
        print "Need to be added to GFORGE_TO_GITHUB_USERNAME_MAPPING() in config.py:"
        print "    %s" % list(localnotfound)

    # check github collaborators list for proper permissions
    githubnoperms = set()
    for k, u in gforge_users.iteritems():
        try:
            found = github_nameduser_by_gforge_userid(k)
            # print "found [%s] as [%s] in collaborators" % ( u['unix_name'], found.login)
        except:
            # print "[%s] not found" % u['unix_name']
            githubnoperms.add(u['unix_name'])
    if len(githubnoperms) > 0:
        errorflag = 1
        print "Need to be added as github collaborators:"
        justgithub = list(githubnoperms - localnotfound)
        print "    %s" % map(github_username_by_gforge_username, justgithub)

    if errorflag == 1:
        exit("ERROR: user mapping is not complete")

def github_username_by_gforge_username( username ):
    return config.GFORGE_TO_GITHUB_USERNAME_MAPPING[username]

def github_nameduser_by_gforge_userid( userid ):
    # gforge username by gforge userid
    gfusername = gforge_users[userid]['unix_name']
    # github username by gforge username
    ghusername = github_username_by_gforge_username(gfusername)
    # list of github namedUsers by github username
    github_matches = [u for u in github_collaborators if u.login == ghusername]
    # return first (and only) match
    return github_matches[0]

def add_trackeritem_to_github( trackeritem ):
    # title
    title = trackeritem.summary.replace("&quot;",'"')

    # body
    ghusername = github_username_by_gforge_username(gforge_users[trackeritem.submitted_by]['unix_name'])
    header = "_Originally Opened: @%s (%s_)" % (ghusername, trackeritem.open_date)
    if trackeritem.close_date != None:
        header = header+"\n_Originally Closed: %s_" % (trackeritem.close_date)
    footer = config.GFORGE_TRACKERITEM_LINK % (config.GFORGE_PROJECT, trackeritem.tracker_item_id)
    body = "%s\n\n%s\n\n\n--\n\n\nFrom: %s" % (header, trackeritem.details, footer)

    # assignee
    assignee = "none"
    print trackeritem.assignees[0].assignee
    if trackeritem.assignees[0].assignee != 100:  # 100 is the system user in GForge
        assignee = github_nameduser_by_gforge_userid(trackeritem.assignees[0].assignee)

    # milestone
    # Milestones can be assigned manually at github.com after import...
    # They are being imported as labels since they are non-standard 'extra_field_data' in GForge
    
    # labels
    labels = [github_label("imported")]
    for f in trackeritem.extra_field_data:
        if (f.field_data != '' and f.field_data != "100" and f.field_data is not None):
            gfe = gforge_elements[int(f.field_data)]
            labels.append(github_label(gfe))

    # truncate long body for github body size limit
    body = body[:65500]

    # create new github issue
    github_issue = github_repo.create_issue(title, body=body, assignee=assignee, labels=labels)

    # add comments
    for m in trackeritem.messages:
        # construct
        ghusername = github_username_by_gforge_username(gforge_users[m.submitted_by]['unix_name'])
        header = "_Original author: @%s (%s)_" % (ghusername, m.adddate)
        content = m.body
        body = "%s\n\n%s" % (header, content)
        # create
        github_comment = github_issue.create_comment(body)

    # close issue if necessary
    if trackeritem.close_date != None:
        github_issue.edit(state="closed")

    # report
    print "trackeritem [%d] --> [%d]... imported" % ( trackeritem.tracker_item_id, github_issue.number )


def migrate_gforge_trackeritems_to_github( trackeritems ):

    # show github rate limit information
    log_github_rate_info()

    # make sure we don't have duplicate items in the passed list
    uniquetrackeritems = {}
    for i in trackeritems:
        uniquetrackeritems[i.tracker_item_id] = i

    # loop through the sorted tracker items
    previous_tiid = 0
    for k, i in sorted(uniquetrackeritems.iteritems()):

        # TODO: determine this number from github directly
        #       set to largest existing github issue id
        skip_to = 1

        if i.tracker_item_id < skip_to:
            previous_tiid += 1
            print "skipping ahead to %d... [%d]" % ( skip_to, i.tracker_item_id )
            continue

        if github.rate_limiting[0] < GITHUB_SPARE_REQUESTS:
            raise Exception("Aborting due to impending GitHub API rate-limit cutoff.")

        # syncronize ids
        github_issue_numbers = [ghi.number for ghi in all_github_issues]
        while previous_tiid + 1 < i.tracker_item_id:
            previous_tiid += 1
            if (previous_tiid not in github_issue_numbers):
                # create new placeholder github issue
                title = "GForge placeholder - trackeritem %d" % previous_tiid
                body = "_This issue is a placeholder to maintain synchronization with imported GForge trackeritem IDs._"
                github_issue = github_repo.create_issue(title, body=body, labels=[github_label("imported")])
                github_issue.edit(state="closed")
                print "--- created placeholder for trackeritem %d --> issue %d" % ( previous_tiid, github_issue.number )

        # prepare new github issue
        log_github_rate_info()
        previous_tiid += 1
        if (i.tracker_item_id not in github_issue_numbers):
            print "creating new issue for trackeritem [%d]" % i.tracker_item_id
            add_trackeritem_to_github( i )
        else:
            print "- skipping previously imported trackeritem [%d]" % i.tracker_item_id

##################################################
if __name__ == "__main__":

    #############################################################################
    # GForge Initialization
    #############################################################################

    # lookup tables for gforge stuff
    gforge_users = {}
    gforge_elements = {}
    # setup GForge SOAP endpoint
    from SOAPpy import SOAPProxy
    GFapi = SOAPProxy(config.GFORGE_ENDPOINT_URL, namespace=config.GFORGE_XML_NAMESPACE)
    # uncomment to see outgoing/incoming XML
    #GFapi.config.debug = 1

    # get GForge session
    GFsession = GFapi.login( config.GFORGE_LOGIN , config.GFORGE_PASSWORD )
    GFuserid = GFsession.split(":")[0]
    # get GForge project
    p = GFapi.getProjectByUnixName(GFsession, config.GFORGE_PROJECT)
    # get all GForge trackers for this project
    trackers = GFapi.getTrackers(GFsession, p.project_id, -1, -1)

    #############################################################################
    # GitHub Initialization
    #############################################################################

    github = Github( config.GITHUB_TOKEN )
    github_user = github.get_user()
    github_label_cache = {}    # to avoid unnecessary API requests
    if "/" in config.GITHUB_PROJECT:
        owner_name, github_project = github_project.split("/")
        try: github_owner = github.get_user(owner_name)
        except GithubException:
            try: github_owner = github.get_organization(owner_name)
            except GithubException:
                github_owner = github_user
    else: github_owner = github_user
    github_repo = github_owner.get_repo(config.GITHUB_PROJECT)
    # get collaborators
    github_collaborators = github_repo.get_collaborators()
    # get milestones
    github_milestones = github_repo.get_milestones()
    # get labels
    github_labels = github_repo.get_labels()
    # get all issues
    all_github_issues = list(github_repo.get_issues(state="open")) + list(github_repo.get_issues(state="closed"))

    #############################################################################
    # do the work
    #############################################################################

    # loop through all GForge trackers
    for t in trackers:
        # more info
        full = GFapi.getTrackerFull(GFsession, t.tracker_id)
        for e in full.extra_field_elements:
            # save for later lookup
            gforge_elements[e.element_id] = e.element_name
            # generate and cache github label for this extra data
            github_label(e.element_name)

        # create new tracker query to page through gracefully
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        qid = GFapi.addTrackerQuery(GFsession, t.tracker_id, GFuserid, "GitHub Migration - %s" % timestamp, 0)

        # page through the new stored query, accumulate the results
        gforge_trackeritems = []
        offset = 0
        GFMAXRESULTS = 50
        while offset < t.item_total:
            items = GFapi.getTrackerItemsFullByQueryId(GFsession, qid, GFMAXRESULTS, offset)
            print "offset[%d] returned[%d] of total[%d]" % ( offset, len(items), t.item_total )
            gforge_trackeritems.extend(items)
            offset += len(items)
            
        # delete tracker query created for this migration
        result = GFapi.deleteTrackerQuery(GFsession, qid)

        # identify all historical users from tracker activity
        userstoadd = set()
        for i in gforge_trackeritems:
            # tracker item creator
            if i.submitted_by not in gforge_users:
                userstoadd.add(i.submitted_by)
            # all message authors
            for m in i.messages:
                if m.submitted_by not in gforge_users:
                    userstoadd.add(m.submitted_by)
            # all commit authors
            for c in i.scm_commits:
                if c.user_id not in gforge_users:
                    userstoadd.add(c.user_id)
            # all assignees
            for a in i.assignees:
                if a.assignee not in gforge_users:
                    userstoadd.add(a.assignee)

        # add them to gforge_users dictionary
        identified_gforge_users = GFapi.getUserArray(GFsession, list(userstoadd))
        for u in identified_gforge_users:
            gforge_users[u.user_id] = {'unix_name': u.unix_name, 'email': u.email}

        # remove gforge system user
        if 100 in gforge_users: del gforge_users[100]

        # check user mapping between gforge and github
        check_user_mapping()

        # migrate gforge tracker items to github
        migrate_gforge_trackeritems_to_github( gforge_trackeritems )
