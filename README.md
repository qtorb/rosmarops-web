# rosmarops-web

Static pages of rosmarops.com that live outside WordPress: the English home (`/`), the Spanish home (`/es/`) and `llms.txt`.

- Edit files under `site/`. A push to `main` starts the deploy workflow, which waits for Albert's approval in the `production` environment and then uploads only those three files to OVH over SFTP. Nothing else on the server is changed or deleted.
- Every public sentence is verified by the product advisor before it lands here.
- The blogs (`/blog/`, `/es/blog/`) are WordPress and are not managed from this repo.
