
class PacketEnums:

    """
    Common packets at root; product/certification overrides in nested classes.

        Define PacketEnums class variables if they are same across products

        Define Product class variables if they are different to product

        Define Certification class varibales if they differ form Certifications

            Example :
                    class PacketEnums:
                        SIGNAL_STRENGTH = "Signal Strength"
                        
                        class MPP:
                            SIGNAL_STRENGTH ="signal strength MPP"

                            class Certification:
                                SIGNAL_STRENGTH ="signal strength Certification"

        Suppose in future the New certification introduces
                Create a class with certification &&
                Assign FALLBACK variable of previous Certification

            Example :
                    class V_2_3_2:
                        Fallback_class = V_2_3_1
        
    """

    SIGNAL_STRENGTH = "Signal Strength"
    IDENTIFICATION = "Identification"
    EXTENDED_IDENTIFICATION = "Extended Identification"
    CONFIGURATION = "Configuration"


    class MPP:

        PLA_2 = "PLA_2" 
        
        class V_2_3_1:

            PLA_2 = "PLA_2 [0x88]"

       

    class C3:

        PLA_2 = "Power Loss Accounting"

        class V_2_3_1:
            
            PLA_2 = "Power Loss Accounting params"

        class V_2_3_2:
            Fallback_class = "V_2_3_1"



class Packet:

    @staticmethod
    def build_packet_class(product=None, certification=None):

        def build_packet_map():
       
            packet_map = {}

            """
                Collect All PacketEnums class varibales
            """
            for key, value in vars(PacketEnums).items():
                if not key.startswith("_") and isinstance(value, str):
                    packet_map[key] = value

            """
                Collect All PacketEnums.product class varibales
            """
            product_class = getattr(PacketEnums, product, None)
            for key, value in vars(product_class).items():
                if not key.startswith("_") and isinstance(value, str):
                    packet_map[key] = value

            """
                Return the Backward Comapatability packets
            """

            if certification  in ["2.0.1","2.1.0","2.2.1","2.0.0","1.3.3"] : return packet_map

            """
                collecting Certification specific packets  
            """
            visited_keys = set()
            certification_name = f'V_{certification.replace(".", "_")}'
            while certification_name is not None:
                certification_class=getattr(product_class, certification_name, None)
                if certification_class is not None: 
                    FallBack=False
                    for key, value in vars(certification_class).items():
                        if key == "Fallback_class":
                            certification_name = value
                            FallBack=True
                            continue
                        if not key.startswith("_") and isinstance(value, str):
                            if key not in visited_keys:
                                visited_keys.add(key)
                                packet_map[key] = value
                    if not FallBack :break    # Break it if there is no fallback defined in the class
                else:break # Break if there is no certification class exists.
            
            return packet_map
        
        for key,value in build_packet_map().items():
            setattr(Packet, key, value)
    