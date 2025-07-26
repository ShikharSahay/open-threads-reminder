package handlers

import (
    "net/http"
    "strconv"
    "database/sql"
    "fmt"
    "strings"
    "time"

    _ "github.com/lib/pq"
    "github.com/labstack/echo/v4"
)

// UserProfile represents a user profile from the database
type UserProfile struct {
    UserID           string `json:"user_id"`
    Name             string `json:"name"`
    DisplayName      string `json:"display_name"`
    RealName         string `json:"real_name"`
    ProfileImageURL  string `json:"profile_image_url"`
    ProfileImage24   string `json:"profile_image_24"`
    ProfileImage32   string `json:"profile_image_32"`
    ProfileImage48   string `json:"profile_image_48"`
    ProfileImage72   string `json:"profile_image_72"`
}

// Thread represents a thread in the database
type Thread struct {
    ThreadTS        string     `json:"thread_ts"`
    ChannelID       string     `json:"channel_id"`
    ChannelName     string     `json:"channel_name"`
    UserID          string     `json:"user_id"`
    ReplyCount      int        `json:"reply_count"`
    LatestReply     time.Time  `json:"latest_reply"`
    Status          string     `json:"status"`
    CreatedAt       time.Time  `json:"created_at"`
    AIThreadName    *string    `json:"ai_thread_name"`
    AIDescription   *string    `json:"ai_description"`
    AIStakeholders  string     `json:"ai_stakeholders"`
    AIPriority      *string    `json:"ai_priority"`
    AIConfidence    *float64   `json:"ai_confidence"`
    GithubIssue     *string    `json:"github_issue"`
    JiraTicket      *string    `json:"jira_ticket"`
    ThreadIssue     *string    `json:"thread_issue"`
    Priority        string     `json:"priority"`
}

// DashboardStats represents dashboard statistics
type DashboardStats struct {
    TotalThreads  int `json:"totalThreads"`
    ActiveThreads int `json:"activeThreads"`
    Channels      int `json:"channels"`
    AIAnalyzed    int `json:"aiAnalyzed"`
}

// GetDashboardStats - Get dashboard statistics
func (c *Container) GetDashboardStats(ctx echo.Context) error {
    db, err := c.getDBConnection()
    if err != nil {
        return ctx.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Database connection failed",
        })
    }
    defer db.Close()

    stats := DashboardStats{}

    // Get total threads across all channels
    var totalThreads int
    err = db.QueryRow("SELECT COUNT(*) FROM channels").Scan(&totalThreads)
    if err == nil {
        // Get actual thread count from channel tables
        rows, err := db.Query("SELECT table_name FROM channels")
        if err == nil {
            defer rows.Close()
            totalCount := 0
            for rows.Next() {
                var tableName string
                if err := rows.Scan(&tableName); err == nil {
                    var count int
                    countQuery := fmt.Sprintf("SELECT COUNT(*) FROM %s", tableName)
                    if err := db.QueryRow(countQuery).Scan(&count); err == nil {
                        totalCount += count
                    }
                }
            }
            stats.TotalThreads = totalCount
        }
    }

    // Get active threads (status = 'open')
    rows, err := db.Query("SELECT table_name FROM channels")
    if err == nil {
        defer rows.Close()
        activeCount := 0
        aiAnalyzedCount := 0
        for rows.Next() {
            var tableName string
            if err := rows.Scan(&tableName); err == nil {
                var count int
                activeQuery := fmt.Sprintf("SELECT COUNT(*) FROM %s WHERE status = 'open'", tableName)
                if err := db.QueryRow(activeQuery).Scan(&count); err == nil {
                    activeCount += count
                }

                // Count AI analyzed threads
                var aiCount int
                aiQuery := fmt.Sprintf("SELECT COUNT(*) FROM %s WHERE ai_thread_name IS NOT NULL", tableName)
                if err := db.QueryRow(aiQuery).Scan(&aiCount); err == nil {
                    aiAnalyzedCount += aiCount
                }
            }
        }
        stats.ActiveThreads = activeCount
        stats.AIAnalyzed = aiAnalyzedCount
    }

    // Get total channels
    err = db.QueryRow("SELECT COUNT(*) FROM channels").Scan(&stats.Channels)
    if err != nil {
        stats.Channels = 0
    }

    return ctx.JSON(http.StatusOK, stats)
}

// GetThreads - Get threads with optional filters
func (c *Container) GetThreads(ctx echo.Context) error {
    db, err := c.getDBConnection()
    if err != nil {
        return ctx.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Database connection failed",
        })
    }
    defer db.Close()

    // Parse query parameters
    limitStr := ctx.QueryParam("limit")
    limit := 10 // default
    if limitStr != "" {
        if parsedLimit, err := strconv.Atoi(limitStr); err == nil && parsedLimit > 0 {
            limit = parsedLimit
        }
    }

    channel := ctx.QueryParam("channel")
    priority := ctx.QueryParam("priority")

    // Get all channel tables
    channelRows, err := db.Query("SELECT channel_id, channel_name, table_name FROM channels")
    if err != nil {
        return ctx.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Failed to get channels",
        })
    }
    defer channelRows.Close()

    allThreads := []Thread{}

    for channelRows.Next() {
        var channelID, channelName, tableName string
        if err := channelRows.Scan(&channelID, &channelName, &tableName); err != nil {
            continue
        }

        // Skip if channel filter is specified and doesn't match
        if channel != "" && channelName != channel {
            continue
        }

        // Build query for this channel's table
        query := fmt.Sprintf(`
            SELECT thread_ts, channel_id, user_id, reply_count, latest_reply, 
                   status, created_at, ai_thread_name, ai_description, 
                   ai_stakeholders, ai_priority, ai_confidence, github_issue, 
                   jira_ticket, thread_issue
            FROM %s 
            WHERE 1=1`, tableName)

        args := []interface{}{}
        argCount := 0

        if priority != "" {
            argCount++
            query += fmt.Sprintf(" AND ai_priority = $%d", argCount)
            args = append(args, priority)
        }

        query += " ORDER BY latest_reply DESC"
        
        if limit > 0 {
            argCount++
            query += fmt.Sprintf(" LIMIT $%d", argCount)
            args = append(args, limit)
        }

        threadRows, err := db.Query(query, args...)
        if err != nil {
            continue // Skip this channel if query fails
        }

        for threadRows.Next() {
            thread := Thread{
                ChannelName: channelName,
            }

            err := threadRows.Scan(
                &thread.ThreadTS, &thread.ChannelID, &thread.UserID,
                &thread.ReplyCount, &thread.LatestReply, &thread.Status,
                &thread.CreatedAt, &thread.AIThreadName, &thread.AIDescription,
                &thread.AIStakeholders, &thread.AIPriority, &thread.AIConfidence,
                &thread.GithubIssue, &thread.JiraTicket, &thread.ThreadIssue,
            )

            if err == nil {
                // Set priority for frontend display
                if thread.AIPriority != nil {
                    thread.Priority = *thread.AIPriority
                } else {
                    thread.Priority = "none"
                }
                allThreads = append(allThreads, thread)
            }
        }
        threadRows.Close()
    }

    // Sort all threads by latest reply and limit
    // (In a real implementation, you might want to do this in the database)
    if len(allThreads) > limit {
        allThreads = allThreads[:limit]
    }

    return ctx.JSON(http.StatusOK, allThreads)
}

// GetChannels - Get all channels
func (c *Container) GetChannels(ctx echo.Context) error {
    db, err := c.getDBConnection()
    if err != nil {
        return ctx.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Database connection failed",
        })
    }
    defer db.Close()

    rows, err := db.Query(`
        SELECT channel_id, channel_name, thread_count, active_thread_count, 
               last_activity, created_at 
        FROM channels
        ORDER BY channel_name
    `)
    if err != nil {
        return ctx.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Failed to query channels",
        })
    }
    defer rows.Close()

    var channels []map[string]interface{}

    for rows.Next() {
        var channelID, channelName string
        var threadCount, activeThreadCount int
        var lastActivity, createdAt time.Time

        err := rows.Scan(&channelID, &channelName, &threadCount, 
                        &activeThreadCount, &lastActivity, &createdAt)
        if err != nil {
            continue
        }

        channel := map[string]interface{}{
            "channel_id":           channelID,
            "channel_name":         channelName,
            "thread_count":         threadCount,
            "active_thread_count":  activeThreadCount,
            "last_activity":        lastActivity,
            "created_at":           createdAt,
        }
        channels = append(channels, channel)
    }

    return ctx.JSON(http.StatusOK, channels)
}

// GetUserProfiles - Get user profiles for stakeholders
func (c *Container) GetUserProfiles(ctx echo.Context) error {
    db, err := c.getDBConnection()
    if err != nil {
        return ctx.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Database connection failed",
        })
    }
    defer db.Close()

    // Get user IDs from query parameter (comma-separated)
    userIDs := ctx.QueryParam("user_ids")
    if userIDs == "" {
        return ctx.JSON(http.StatusBadRequest, map[string]string{
            "error": "user_ids parameter is required",
        })
    }

    // Split user IDs and prepare query
    userIDList := strings.Split(userIDs, ",")
    if len(userIDList) == 0 {
        return ctx.JSON(http.StatusOK, []UserProfile{})
    }

    // Build the query with placeholders
    placeholders := make([]string, len(userIDList))
    args := make([]interface{}, len(userIDList))
    for i, userID := range userIDList {
        placeholders[i] = fmt.Sprintf("$%d", i+1)
        args[i] = strings.TrimSpace(userID)
    }

    query := fmt.Sprintf(`
        SELECT user_id, name, display_name, real_name, 
               profile_image_url, profile_image_24, profile_image_32, 
               profile_image_48, profile_image_72
        FROM user_profiles 
        WHERE user_id IN (%s)
    `, strings.Join(placeholders, ","))

    rows, err := db.Query(query, args...)
    if err != nil {
        return ctx.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Failed to query user profiles",
        })
    }
    defer rows.Close()

    var profiles []UserProfile
    for rows.Next() {
        var profile UserProfile
        err := rows.Scan(
            &profile.UserID, &profile.Name, &profile.DisplayName, &profile.RealName,
            &profile.ProfileImageURL, &profile.ProfileImage24, &profile.ProfileImage32,
            &profile.ProfileImage48, &profile.ProfileImage72,
        )
        if err != nil {
            continue
        }
        profiles = append(profiles, profile)
    }

    return ctx.JSON(http.StatusOK, profiles)
}

// getDBConnection creates a database connection
func (c *Container) getDBConnection() (*sql.DB, error) {
    // Database configuration - in production, use environment variables
    dbConfig := map[string]string{
        "host":     "10.150.3.246",
        "port":     "5433",
        "user":     "yugabyte",
        "password": "Threads@123",
        "dbname":   "open_thread_db",
        "sslmode":  "disable",
    }

    connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
        dbConfig["host"], dbConfig["port"], dbConfig["user"], 
        dbConfig["password"], dbConfig["dbname"], dbConfig["sslmode"])

    db, err := sql.Open("postgres", connStr)
    if err != nil {
        return nil, err
    }

    // Test the connection
    if err := db.Ping(); err != nil {
        db.Close()
        return nil, err
    }

    return db, nil
} 