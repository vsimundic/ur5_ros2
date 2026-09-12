uint8 NOT_AVAILABLE=0
uint8 DRAFT_STARTED=1
uint8 P0_CAPTURED=2
uint8 PX_CAPTURED=3
uint8 PY_CAPTURED=4
uint8 VALIDATED=5
uint8 INVALID=6
uint8 ACCEPTED=7

uint8 state
bool active_valid
string active_calibration_id
string reason_code
string[] captured_points
