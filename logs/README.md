# Logs Directory

This directory contains application log files for debugging and monitoring.

## Log Files

### 1. `error.log`
- **Purpose**: Contains only ERROR and CRITICAL level messages
- **Rotation**: 10 MB per file, keeps 5 backups
- **Use**: Quick reference for critical issues and errors

### 2. `debug.log`
- **Purpose**: Contains ALL log messages (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Rotation**: 20 MB per file, keeps 5 backups
- **Use**: Comprehensive debugging and tracing

### 3. `template_api.log`
- **Purpose**: Dedicated log for WhatsApp Template API operations
- **Rotation**: 20 MB per file, keeps 5 backups
- **Use**: Debug template creation, Meta API calls, and template-related issues
- **Contains**:
  - Incoming API requests with full payloads
  - Template service operations with detailed steps
  - Meta WhatsApp API calls and responses
  - Detailed error traces with full stack traces
  - PyWa client interaction details

## Log Format

**Error Log Format:**
```
2025-12-01 16:30:45 | ERROR | template_api | template_service.py:180 | Error message
Stack trace...
```

**Debug Log Format:**
```
2025-12-01 16:30:45 | DEBUG    | template_api                  | template_service.py:116 | Debug message
```

**Template API Log Format:**
```
2025-12-01 16:30:45 | INFO     | Detailed message about API operations
```

## Debugging Template Issues

When debugging template creation issues, check `template_api.log` for:

1. **API Request Details**: Full request payload sent to the endpoint
2. **WhatsApp Client Status**: Whether the client is initialized
3. **Meta API Call**: Details of the API call to Meta WhatsApp
4. **API Response**: Full response or error from Meta
5. **Error Traces**: Complete stack traces for any failures

## Log Rotation

All logs automatically rotate to prevent disk space issues:
- Old logs are renamed with `.1`, `.2`, etc.
- Oldest logs are automatically deleted
- Rotation happens when file size exceeds the limit

## Viewing Logs

```bash
# View latest template API logs
tail -f logs/template_api.log

# View all errors
tail -f logs/error.log

# Search for specific template
grep "template_name_here" logs/template_api.log

# View last 100 lines
tail -n 100 logs/debug.log
```

## Note

This directory and its contents are excluded from git via `.gitignore`.
