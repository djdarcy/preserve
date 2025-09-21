@echo off
echo Testing RESTORE Verbosity System
echo ================================
echo.

echo Test 1: Default output (minimal)
echo ---------------------------------
preserve RESTORE --src .\private\dst2
echo.
pause

echo Test 2: Verbose level 1 (-v)
echo -----------------------------
preserve RESTORE --src .\private\dst2 -v
echo.
pause

echo Test 3: Verbose level 2 (-vv)
echo ------------------------------
preserve RESTORE --src .\private\dst2 -vv
echo.
pause

echo Test 4: Verbose level 3 (-vvv)
echo -------------------------------
preserve RESTORE --src .\private\dst2 -vvv
echo.
pause

echo Test 5: Quiet mode (--quiet)
echo -----------------------------
preserve RESTORE --src .\private\dst2 --quiet
echo.
pause

echo Test 6: No color output
echo ------------------------
preserve RESTORE --src .\private\dst2 -v --no-color
echo.
pause

echo Test 7: Dry run with verbose
echo -----------------------------
preserve RESTORE --src .\private\dst2 -v --dry-run
echo.

echo All tests complete!
pause