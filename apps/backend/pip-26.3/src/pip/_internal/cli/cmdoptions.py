s,
    ],
}

index_group: dict[str, Any] = {
    "name": "Package Index Options",
    "options": [
        index_url,
        extra_index_url,
        no_index,
        refresh_package,
        find_links,
        uploaded_prior_to,
    ],
}

package_selection_group: dict[str, Any] = {
    "name": "Package Selection Options",
    "options": [
        pre,
        all_releases,
        only_final,
        no_binary,
        only_binary,
        prefer_binary,
    ],
}
