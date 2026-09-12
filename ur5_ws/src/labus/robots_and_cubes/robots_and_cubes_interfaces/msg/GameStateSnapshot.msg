uint8 EASY=0
uint8 BEGINNER=1
uint8 STANDARD=2
uint8 CHALLENGE=3

uint8 RIGHT=0
uint8 LEFT=1

uint8 OPERATION_IDLE=0
uint8 OPERATION_EXECUTING=1
uint8 OPERATION_RECONCILIATION_REQUIRED=2

uint32 schema_version
uint64 state_version
string round_id
uint8 mode
string game_state
int32 origin_column
int32 origin_row
uint16 rotation_deg
uint8 handedness
bool has_beginner_target
int32 beginner_target_game_x
int32 beginner_target_game_y
robots_and_cubes_interfaces/CubeState[] cubes
string[] answer_order
string[] selected_answer_ids
string[] disabled_answer_ids
int32 attempts_remaining
uint8 robot_operation_state
string pending_request_id
string pending_operation_id
bool game_flow_ready
robots_and_cubes_interfaces/ErrorSummary recoverable_error
