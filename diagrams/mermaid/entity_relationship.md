%% Entity Relational Diagram written in MermaidJS
erDiagram
    USER ||--o{ FILE : "has uploaded"
    USER ||--o{ CHAT : has
    USER ||--o{ FOLDER : has
    USER ||--o{ NOTIFICATION : "has been sent"
    USER {
        string id "PK,FK"
        string name
        string email
        string role
        string profile_image_url
        string domain
        bigint last_active
        bigint updated_at
        bigint created_at
        string api_key
        json settings
        json info
    }
    CHAT {
      string id "PK"
      string user_id "FK"
      string title
      json chat
      bigint updated_at
      bigint created_at
      string share_id "nullable, unique"
      bool archived
      bool pinned "nullable"
      json meta
      string folder_id "FK"
    }
    CHAT }o--|| FOLDER : "are in a"
    FILE {
        string id "PK"
        string user_id "FK"
        string hash "nullable"
        string filename
        string path "nullable"
        json data "nullable"
        json meta "nullable"
        json access_control "nullable"
        bigint created_at
        bigint updated_at
    }
    FOLDER |o--o| FOLDER : "has parent"
    FOLDER {
      string id "PK"
      string parent_id "FK,nullable"
      string user_id "FK"
      string name
      json items "nullable"
      json meta "nullable"
      bool is_expanded
      bigint created_at
      bigint updated_at
    }
    MESSAGE |o--o| MESSAGE : "has parent"
    MESSAGE |o--o| CHANNEL : "has a"
    MESSAGE {
      string id "PK"
      string user_id "FK"
      string channel_id "FK"
      string parent_id "FK"
      string content
      json data "nullable"
      json meta "nullable"
      bigint created_at
      bigint updated_at
    }
    NOTIFICATION {
      string id "PK"
      string user_id "FK"
      string type
      bool delivered
      bigint created_at
      bigint updated_at
    }
