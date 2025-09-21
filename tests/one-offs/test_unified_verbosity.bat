@echo off
echo Testing Unified Verbosity System
echo =================================
echo.

echo Test 1: RESTORE with quiet mode
echo --------------------------------
preserve RESTORE --src .\private\dst2 --quiet
echo.

echo Test 2: RESTORE with verbose (-v)
echo ----------------------------------
preserve RESTORE --src .\private\dst2 -v 2>&1 | find /c "Restoring"
echo.

echo Test 3: COPY help shows verbosity flags
echo ----------------------------------------
preserve COPY --help | find "verbose"
echo.

echo Test 4: MOVE help shows verbosity flags
echo ----------------------------------------
preserve MOVE --help | find "verbose"
echo.

echo Test 5: VERIFY help shows verbosity flags
echo ------------------------------------------
preserve VERIFY --help | find "verbose"
echo.

echo Test 6: CONFIG help shows verbosity flags
echo ------------------------------------------
preserve CONFIG --help | find "verbose"
echo.

echo All tests complete!