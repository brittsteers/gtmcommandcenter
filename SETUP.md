# Cloud setup

This gets the agents running on GitHub Actions, signed in to Claude through workload identity federation, with the dashboard on GitHub Pages. It takes about 20 minutes.

The code lives in the public repo `brittsteers/gtmcommandcenter`. The local working folder is `/Users/Brittany/launch-command-center`, and its commits use the GitHub noreply email so a personal email never appears on the repo.

## 1. Repository

Done: `https://github.com/brittsteers/gtmcommandcenter` is public. Public keeps Actions minutes and Pages free, and every launch in it is fictional.

## 2. Push the code

In **GitHub Desktop**:

1. Choose **File > Add Local Repository** and pick `/Users/Brittany/launch-command-center`. It's already connected to `brittsteers/gtmcommandcenter`.
2. Click **Push origin**.

The earlier clone in `~/Documents/GitHub/gtmcommandcenter` only holds the starter README. You can remove it from GitHub Desktop (right-click > **Remove**) so you don't edit the wrong copy.

## 3. Repository settings

In the repo on GitHub, open **Settings**:

- **Actions > General > Workflow permissions:** select **Read and write permissions** and check **Allow GitHub Actions to create and approve pull requests**. The plan workflow needs this to open the risk review PR.
- **Pages > Build and deployment > Source:** select **GitHub Actions**.

## 4. Connect Claude through workload identity federation

You need an Anthropic Console account with billing set up and the admin or owner role in your organization.

1. Go to platform.claude.com/settings/workload-identity-federation and click **Connect workload**.
2. Choose the **GitHub Actions** tile and enter:

   | Field | Value |
   |---|---|
   | Issuer URL | `https://token.actions.githubusercontent.com` (prefilled) |
   | Subject prefix | `repo:brittsteers@200021320/gtmcommandcenter@1444697016:ref:refs/heads/main` |
   | Audience | `https://api.anthropic.com` |
   | Claim `repository_owner` | `brittsteers` |
   | Scope | `workspace:developer` (prefilled) |
   | Token lifetime | `600` seconds (prefilled) |

   The subject prefix only trusts workflow runs on `main` in this one repository. Pull requests from forks can't get a token.

   New GitHub repos use immutable subject claims, which add the owner and repo numeric IDs after an `@`. The IDs mean a renamed or re-registered repo can't reuse this rule. Check the exact prefix at `https://api.github.com/repos/brittsteers/gtmcommandcenter/actions/oidc/customization/sub` (the `sub_claim_prefix` field).

3. Note the **federation rule ID** (`fdrl_...`) and **service account ID** (`svac_...`) the wizard creates. Your **organization ID** is on platform.claude.com/settings/organization.

4. In the GitHub repo, open **Settings > Secrets and variables > Actions > Variables** and add:

   | Variable | Value |
   |---|---|
   | `ANTHROPIC_FEDERATION_RULE_ID` | `fdrl_...` |
   | `ANTHROPIC_ORGANIZATION_ID` | your organization ID |
   | `ANTHROPIC_SERVICE_ACCOUNT_ID` | `svac_...` |
   | `ANTHROPIC_WORKSPACE_ID` | only if the rule covers more than one workspace |

   These are **variables, not secrets**. None of them is a credential. Access comes from GitHub's signed token, which only exists inside a matching workflow run.

The wizard listens for a successful sign-in for 15 minutes. Starting step 5 within that window confirms the setup.

## 5. Run it

1. **Actions > 1 · Plan launch > Run workflow.** The agents take a few minutes. When they finish, a pull request named "Risk review: Nova 2 model launch" appears.
2. **Review the risks in the PR.** Edit `runs/<run-id>/review.yaml`, set `decision: reject` on anything you disagree with, and rewrite a mitigation if you'd like. Commit to the PR branch.
3. **Merge the PR.** That's the approval. **2 · Finalize launch status** runs the Synthesizer, commits the status and republishes the dashboard.
4. **Open the dashboard** at `https://brittsteers.github.io/gtmcommandcenter/`. Your live run is listed above the sample.

## If something fails

- **"Missing repository variables"**: step 4 isn't finished.
- **401 `Authentication failed`**: open the authentication history tab on the Console's Workload identity page. `match_subject_prefix` means the subject prefix doesn't match GitHub's token. Compare it with `sub_claim_prefix` from the URL in step 4.
- **"GitHub Actions is not permitted to create pull requests"**: the checkbox in step 3 is off.
- **The dashboard 404s**: Pages source isn't set to GitHub Actions. Then run **3 · Publish dashboard** once by hand.

Each live run makes six model calls (one on Opus, five on Sonnet), which costs well under a dollar.
