# open-threads-reminder dashboard

UI dashboard for the open-threads-reminder Slack app.

# Prerequisites

- Go version 1.23 or greater
- Node version 20 or greater

# Development Build

For development purposes, you may want to run the UI and backend API server separately to avoid
having to run the `build.sh` script every time. To do this, run `npm run dev` to start the
frontend, and `go run main.go` to run the backend. The UI will be accessible at `127.0.0.1:5173`.

# Build and Run Binary

1. Run the `build.sh` script to generate the binary at `build/dashboard`.
    ```sh
    ./build.sh
    ```

3. Run the `dashboard` binary. The UI will be accessible at `127.0.0.1:18080` by default.
    ```sh
    build/pgcompare
    ```

# Configure

The following environment variables may be used to configure the application:

`YB_OPEN_THREADS_REMINDER_ADDR`  
&nbsp; &nbsp; &nbsp; &nbsp; Address that the UI will be served on.  
&nbsp; &nbsp; &nbsp; &nbsp; Default: `127.0.0.1`  

`YB_OPEN_THREADS_REMINDER_PORT`  
&nbsp; &nbsp; &nbsp; &nbsp; Port that the UI will be served on.  
&nbsp; &nbsp; &nbsp; &nbsp; Default: `18080`  

