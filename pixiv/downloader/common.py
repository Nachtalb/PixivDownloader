from prompt_toolkit.shortcuts import print_formatted_text

REFRESH_TOKEN_LINK = "https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362"
UPWD_PROBLEM_LINK = "https://github.com/upbit/pixivpy/issues/158#issuecomment-777815440"


def print_upwd_deprecated_warning():
    warning = (
        f"It's not possible anymore to login with username and password. Please see {UPWD_PROBLEM_LINK} for more"
        " information. You have to get a refresh token via a workflow like this and enter it instead:"
        f" {REFRESH_TOKEN_LINK}"
    )
    print_formatted_text({warning: "#ff0066"})
    return warning
