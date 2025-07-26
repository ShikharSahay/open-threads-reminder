package apiserver

import (
    "dashboard/apiserver/handlers"
    "dashboard/apiserver/logger"
    "dashboard/apiserver/templates"

    "embed"
    "io/fs"
    "net"
    "net/http"
    "os"
    "strconv"
    "time"

    "html/template"

    "github.com/labstack/echo/v4"
    "github.com/labstack/echo/v4/middleware"
)

const logLevelEnv string = "YB_OPEN_THREADS_REMINDER_DASHBOARD_UI_LOG_LEVEL"

const (
    uiDir     = "dist"
    extension = "/*.html"
)

//go:embed dist
var staticFiles embed.FS

var templatesMap map[string]*template.Template

func getEnv(key, fallback string) string {
    if value, ok := os.LookupEnv(key); ok {
        return value
    }
    return fallback
}

func LoadTemplates() error {

    if templatesMap == nil {
        templatesMap = make(map[string]*template.Template)
    }

    templateFiles, err := fs.ReadDir(staticFiles, uiDir)
    if err != nil {
        return err
    }

    for _, tmpl := range templateFiles {
        if tmpl.IsDir() {
            continue
        }

        file, err := template.ParseFS(staticFiles, "dist/index.html")
        if err != nil {
            return err
        }

        templatesMap[tmpl.Name()] = file
    }
    return nil
}

func getStaticFiles() http.FileSystem {

    println("using embed mode")
    fsys, err := fs.Sub(staticFiles, "dist")
    if err != nil {
        panic(err)
    }

    return http.FS(fsys)
}

func Start(bindAddr string, port string) {

    // Initialize logger
    logLevel := getEnv(logLevelEnv, "info")
    var logLevelEnum logger.LogLevel
    switch logLevel {
    case "debug":
        logLevelEnum = logger.Debug
    case "info":
        logLevelEnum = logger.Info
    case "warn":
        logLevelEnum = logger.Warn
    case "error":
        logLevelEnum = logger.Error
    default:
        println("unknown log level env variable, defaulting to info level logging")
        logLevel = "info"
        logLevelEnum = logger.Info
    }
    log, _ := logger.NewLogger(logLevelEnum)
    defer log.Cleanup()
    log.Infof("Logger initialized with %s level logging", logLevel)

    LoadTemplates()

    e := echo.New()

    c, _ := handlers.NewContainer(log)

    // Middleware
    e.Use(middleware.RecoverWithConfig(middleware.RecoverConfig{
        LogErrorFunc: func(c echo.Context, err error, stack []byte) error {
            log.Errorf("[PANIC RECOVER] %v %s\n", err, stack)
            return nil
        },
    }))
    e.Use(middleware.RequestLoggerWithConfig(middleware.RequestLoggerConfig{
        LogURI:           true,
        LogStatus:        true,
        LogLatency:       true,
        LogMethod:        true,
        LogContentLength: true,
        LogResponseSize:  true,
        LogUserAgent:     true,
        LogHost:          true,
        LogRemoteIP:      true,
        LogRequestID:     true,
        LogError:         true,
        LogValuesFunc: func(c echo.Context, v middleware.RequestLoggerValues) error {
            bytes_in, err := strconv.ParseInt(v.ContentLength, 10, 64)
            if err != nil {
                bytes_in = 0
            }
            err = v.Error
            errString := ""
            if err != nil {
                errString = err.Error()
            }
            log.With(
                "time", v.StartTime.Format(time.RFC3339Nano),
                "id", v.RequestID,
                "remote_ip", v.RemoteIP,
                "host", v.Host,
                "method", v.Method,
                "URI", v.URI,
                "user_agent", v.UserAgent,
                "status", v.Status,
                "error", errString,
                "latency", v.Latency.Nanoseconds(),
                "latency_human", time.Duration(v.Latency.Microseconds()).String(),
                "bytes_in", bytes_in,
                "bytes_out", v.ResponseSize,
            ).Infof(
                "request",
            )
            return nil
        },
    }))
    e.Use(middleware.GzipWithConfig(middleware.GzipConfig{
      Level: 2,
      MinLength: 4096,
    }))
    
    // CORS middleware for frontend-backend communication
    e.Use(middleware.CORSWithConfig(middleware.CORSConfig{
        AllowOrigins:     []string{"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"},
        AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"},
        AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization", "X-Requested-With", "X-HTTP-Method-Override"},
        AllowCredentials: false,
        ExposeHeaders:    []string{"Content-Length", "Content-Type"},
        MaxAge:           86400, // 24 hours
    }))

    // API endpoints
    e.GET("/api/sample_get", c.GetSample)
    e.POST("/api/sample_post", c.PostSample)
    
    // Thread Dashboard API endpoints
    e.GET("/api/stats", c.GetDashboardStats)
    e.GET("/api/threads", c.GetThreads)
    e.GET("/api/channels", c.GetChannels)
    e.GET("/api/user-profiles", c.GetUserProfiles)

    render_htmls := templates.NewTemplate()

    render_htmls.Add("index.html", templatesMap["index.html"])
    assetHandler := http.FileServer(getStaticFiles())
    e.GET("/*", echo.WrapHandler(http.StripPrefix("/", assetHandler)))
    e.Renderer = render_htmls
    e.GET("/", handlers.IndexHandler)

    uiBindAddress := net.JoinHostPort(bindAddr, port)
    e.Logger.Fatal(e.Start(uiBindAddress))
}
