"""
Default CMS role definitions.

Permissions are matched by app label and action rather than listed individually,
so the roles stay correct as content models arrive in later phases — they grant
whatever exists at the time they are synced.

Both the bootstrap migration and the `sync_cms_groups` management command use
this one definition, so there is no second copy to drift.
"""

CONTENT_APPS = [
    "projects",
    "services",
    "blogs",
    "faqs",
    "sections",
    "pages",
    "media_library",
    "enquiries",
]

GROUPS = {
    # Everything content-related, plus user and group management.
    "Administrators": {
        "apps": CONTENT_APPS + ["auth", "audit"],
        "actions": ["view", "add", "change", "delete"],
    },
    # All content, but no control over who else can log in.
    "Content Managers": {
        "apps": CONTENT_APPS,
        "actions": ["view", "add", "change", "delete"],
    },
    # Can write and revise, cannot destroy.
    "Editors": {
        "apps": CONTENT_APPS,
        "actions": ["view", "add", "change"],
    },
    # The media library only.
    "Media Managers": {
        "apps": ["media_library"],
        "actions": ["view", "add", "change", "delete"],
    },
}


def sync_groups(Group, Permission):
    """Create the roles and grant their permissions.

    Additive and idempotent: never removes permissions an administrator granted
    by hand, and safe to re-run after new apps are added.

    Takes the models as arguments so a migration can pass its historical
    versions.
    """
    report = {}

    for name, spec in GROUPS.items():
        group, _ = Group.objects.get_or_create(name=name)

        candidates = Permission.objects.filter(
            content_type__app_label__in=spec["apps"]
        )
        wanted = [
            permission
            for permission in candidates
            if permission.codename.split("_")[0] in spec["actions"]
        ]
        if wanted:
            group.permissions.add(*wanted)

        report[name] = len(wanted)

    return report
