

# SmaliAssemblyInstructions.py
#
# Each of these classes is basically in thin wrapper around a string 
# They correspond to the instructions for smali bytecode as listed
# here: http://pallergabor.uw.hu/androidblog/dalvik_opcodes.html
# Implementation is incomplete.  Only the instructions necessary 
# for taint-tracking implementation of the stigma project are present.


# When adding a new class to this file
# please consider the class hierarchy so far 
# (please update this comment)
#
# Should the new class be a child of SmaliAssemblyInstruction?
# Should the new class be a child of MOVE?
# Should the new class be a child of _SINGLE_DEST_REGISTER_INSTRUCTION?
#   * Note: _SINGLE_DEST_REGISTER_INSTRUCTION is any instruction that
#           only has ONE parameter; a register that serves as a destination.
# Should the new class be a child of CONST?
# Should the new class be a child of MOVE-RESULT?

# Here are some of the "abstract" parent classes
# _SINGLE_REGISTER_INSTRUCTION
# _SINGLE_DEST_REGISTER_INSTRUCTION
# _PARAMETER_LIST_INSTRUCTION
# _TRIPLE_REGISTER_INSTRUCTION
# _TWO_REG_EQ
# _ONE_REG_EQ_ZERO
# _I_INSTRUCTION
# _I_INSTRUCTION_QUICK
# _S_INSTRUCTION
# _INVOKE_INSTRUCTION
# _TWO_REGISTER_UNARY_INSTRUCTION
# _TWO_REGISTER_BINARY_INSTRUCTION
# _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION

import StigmaStringParsingLib
import SmaliTypes

from SmaliRegister import SmaliRegister


class SmaliAssemblyInstruction():

    
    @staticmethod
    def from_line(raw_line_string):
        #print("constructing SmaliAssemblyInstruction From: " + str(raw_line_string))

        line = raw_line_string.strip("\n")
        if(StigmaStringParsingLib.is_comment(line)):
            return COMMENT(line)

        hash_pos = line.find("#")
        if hash_pos != -1:
            # for now, delete "in-line" comments since they're a pain to retain
            line = line[:hash_pos] 


        
        tokens = StigmaStringParsingLib.break_into_tokens(line)
        #tokens = list(filter(lambda x: x != "", tokens)) # removes ""
        #print("tokens: " + str(tokens))
        if(len(tokens) == 0):
            return BLANK_LINE()


        opcode = tokens[0]

        if(opcode == "const-string"):
            return CONST_STRING(tokens[1].strip(","), "\"" + line.split("\"")[1] + "\"")
        

        if(opcode_has_parameter_list(opcode) or opcode_has_parameter_range(opcode)):
            start = line.index("{")
            end = line.index("}")
            args = line[start+1:end]
            #print("HERE")
            #print(args)
            if args == "":
                args = "[]"
            else:
                args = args.split(" ")
                args = str(list(map(lambda x : x.strip(","), args)))
            
            args = [ args ]
            args.append("\"" + tokens[-1] + "\"")
            #print("args before: " + str(args))
            
            
        else:
            args = tokens[1:]
            #print("args before: " + str(args))
            args = list(map(lambda x : "\"" + str(x.strip(",")) + "\"", args))
            
        #print("args: " + str(args))


        opcode = opcode.upper()
        opcode = opcode.replace("/", "_")
        opcode = opcode.replace("-", "_")

        # this next part is very very technical and feels
        # pretty hacky
        # https://www.programiz.com/python-programming/methods/built-in/eval
        # https://stackoverflow.com/questions/3941517/converting-list-to-args-when-calling-function#3941529
        # example input line: "    move/from16 v1, v25"
        # output eval_string: "MOVE_FROM16("v1", "v25")"
        eval_string = opcode + "(" + ", ".join(args) + ")"
        #print("eval_string: " + eval_string)

        try:
            #print("eval string: " + str(eval_string))
            smali_assembly_instruction_obj = eval(eval_string)
            return smali_assembly_instruction_obj
        except Exception as e:
            print("Exception in eval, parse_line(): " + str(e))

    
    def __str__(self):
        return "    " + repr(self) + "\n"

    def get_registers(self):
        return []

    def get_p_registers(self):
        return list(filter(lambda x : x[0] == "p", self.get_registers()))
        
    def get_implicit_registers(self):
        return []

    def __eq__(self, other):
        return repr(self) == repr(other)
    
    def get_move(self):
        return MOVE_16

    def get_unique_registers(self):
        ans = []
        for item in self.get_registers():
            if(item not in ans):
                ans.append(item)
        return ans
        
    def get_register_type_implications(self):
        return {}
    

class _ImplicitRegistersInstruction():
    # instructions that have implicit registers
    # all such cases are "wide" instructions that 
    # work with 64-bit types Long, or Double
    def get_implicit_registers(self):
        ans = []
        for reg in self.get_registers():
            implicit_reg = reg + 1
            ans.append(implicit_reg)
        return ans
        
class _ImplicitFirstRegisterInstruction():
    # the first register (and only that register)
    # specifies a "wide" type such as Long or Double
    def get_implicit_registers(self):
        regs = self.get_registers()
        return [regs[0] + 1]
        
        
class _ThirtyTwoBit_Parameters():
    # instruction classes that extend this type
    # are those in which ALL the registers/parameters
    # are 32-bit types
    def get_register_type_implications(self):
        ans = {}
        for reg in self.get_registers():
            ans[reg] = SmaliTypes.ThirtyTwoBit()
        return ans
        
class _Object_Parameters():
    # instruction classes that extend this type
    # are those in which ALL the registers/parameters
    # are object types
    def get_register_type_implications(self):
        ans = {}
        for reg in self.get_registers():
            ans[reg] = SmaliTypes.NonSpecificObjectReference()
        return ans
        
class _SixtyFourBit_Dest():
    # instruction classes that extend this type
    # are those in which ALL the registers/parameters
    # are wide / "64-bit" types
    def get_register_type_implications(self):
        
        # consider the follow example
        # e.g., add-long v6, v0, v5
        # this instruction (found in the wild) re-writes
        # v6 from it's incoming value (64-bit-2) to
        # it's new value (64-bit) outgoing
        # thereby invalidating the value stored in v5
        # because of this annoying edge-case I chose to implement
        # type implications only for the dest reg
        
        explicit_regs = self.get_registers()
        implicit_regs = self.get_implicit_registers()
                
        ans = {}
        ans[explicit_regs[0]] = SmaliTypes.SixtyFourBit()
        ans[implicit_regs[0]] = SmaliTypes.SixtyFourBit_2() 
    
        return ans
        
#class _NoType_OR_NoParameters():
    # instruction classes that extend this type
    # are those in which (1) there are no parameters
    # or (2) the parameters given do not have any type rules
#    def get_register_type_implications(self):
#        return {}


class NOP(SmaliAssemblyInstruction):
    def __repr__(self):
        return self.opcode()
        
    def opcode(self):
        return "nop"
        

class INVOKE_DIRECT_EMPTY(NOP):
    # could not find any instance of this instruction
    # in our APK files
    # From the documentation:
    #   "Stands as a placeholder for pruned empty methods 
    #   like Object.<init>. This acts as nop during 
    #   normal execution."
    def opcode(self):
        return "invoke-direct-empty"


class BLANK_LINE(SmaliAssemblyInstruction):
    def __repr__(self):
        return ""


class COMMENT(SmaliAssemblyInstruction):
    def __init__(self, line):
        self.l = line

    def __repr__(self):
        return "# " + self.l


class MOVE(_ThirtyTwoBit_Parameters, SmaliAssemblyInstruction):
    def __init__(self, reg1, reg2):
        self.reg1 = SmaliRegister(reg1)
        self.reg2 = SmaliRegister(reg2)

    def get_registers(self):
        if(self.reg1 == ""):
            raise UnboundLocalError("reg1")
        if(self.reg2 == ""):
            raise UnboundLocalError("reg2")
        return [self.reg1, self.reg2]
        
    def opcode(self):
        return "move"

    def __repr__(self):
        return self.opcode() + " " + str(self.reg1) + ", " + str(self.reg2)


class MOVE_16(MOVE):
    # this might not exist
    # I couldn't find any occurrences in the smali of leaks
    
    def opcode(self):
        return "move/16"
    
    def __repr__(self):
        return self.opcode() + " " + str(self.reg1) + ", " + str(self.reg2)
        

# This is a problem
# I need the class name to be MOVE/FROM16
# but "/" is not a valid character in a class name
class MOVE_FROM16(MOVE):
    
    def opcode(self):
        return "move/from16"
    
    def __repr__(self):
        return self.opcode() + " " + str(self.reg1) + ", " + str(self.reg2)

# This is a minor inconvenience
# I need the class name to be MOVE-WIDE
# but "-" is not a valid character in a class name
class MOVE_WIDE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, MOVE):
    def opcode(self):
        return "move-wide"
    
class MOVE_WIDE_FROM16(MOVE_WIDE):
    def opcode(self):
        return "move-wide/from16"

class MOVE_WIDE_16(MOVE_WIDE):
    def opcode(self):
        return "move-wide/16"

class MOVE_OBJECT(_Object_Parameters, MOVE):
    def opcode(self):
        return "move-object"
        
class MOVE_OBJECT_FROM16(MOVE_OBJECT):
    def opcode(self):
        return "move-object/from16"

class MOVE_OBJECT_16(MOVE_OBJECT):
    def opcode(self):
        return "move-object/16"

class _SINGLE_REGISTER_INSTRUCTION(SmaliAssemblyInstruction):
    def __init__(self, reg_dest):
        self.rd = SmaliRegister(reg_dest)

    def get_registers(self):
        return [self.rd]

    def __repr__(self):
        return self.opcode() + " " + str(self.rd)


class _SINGLE_DEST_REGISTER_INSTRUCTION(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly.
    #   * Note: _SINGLE_DEST_REGISTER_INSTRUCTION is any instruction that
    #   only has ONE parameter; a register that serves as a destination.
    def __init__(self, reg_dest, value_arg):
        self.rd = SmaliRegister(reg_dest)
        self.value_arg = value_arg

    def get_registers(self):
        return [self.rd]
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.value_arg)


class MOVE_RESULT(_ThirtyTwoBit_Parameters, _SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "move-result"

class MOVE_RESULT_WIDE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "move-result-wide"

class MOVE_RESULT_OBJECT(_Object_Parameters, _SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "move-result-object"

class MOVE_EXCEPTION(_Object_Parameters, _SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "move-exception"

class RETURN_VOID(SmaliAssemblyInstruction):
    def opcode(self):
        return "return-void"
        
    def __repr__(self):
        return self.opcode()

class RETURN(_ThirtyTwoBit_Parameters, _SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "return"

class RETURN_WIDE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "return-wide"

class RETURN_OBJECT(_Object_Parameters, _SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "return-object"



class CONST(_ThirtyTwoBit_Parameters, _SINGLE_DEST_REGISTER_INSTRUCTION):
        
    def opcode(self):
        return "const"


class CONST_4(CONST):
    def opcode(self):
        return "const/4"

class CONST_16(CONST):
    def opcode(self):
        return "const/16"

class CONST_HIGH16(CONST):
    def opcode(self):
        return "const/high16"

class CONST_WIDE(_ImplicitRegistersInstruction, _SixtyFourBit_Dest, CONST):
    def opcode(self):
        return "const-wide"

class CONST_WIDE_16(CONST_WIDE):
    def opcode(self):
        return "const-wide/16"

class CONST_WIDE_32(CONST_WIDE):
    def opcode(self):
        return "const-wide/32"

class CONST_WIDE_HIGH16(CONST_WIDE):
    def opcode(self):
        return "const-wide/high16"


class CONST_STRING(_SINGLE_DEST_REGISTER_INSTRUCTION):
    
    def opcode(self):
        return "const-string"
        
    def get_register_type_implications(self):
        return {self.rd: SmaliTypes.ObjectReference("Ljava/lang/String;")}
        

class CONST_STRING_JUMBO(SmaliAssemblyInstruction):
    # https://stackoverflow.com/questions/19991833/in-dalvik-what-expression-will-generate-instructions-not-int-and-const-strin
    # found one in com.amazon.avod.thirdpartyclient.apk 
    #       const-string/jumbo v5, "stackTrace"
    def __init__(self, ):
        print("not yet implemented: const-string/jumbo")
        raise Execption("Not Yet Implemented!")
        pass
        
    def get_register_type_implications(self):
        return {self.rd: SmaliTypes.ObjectReference("Ljava/lang/String;")}
        

class CONST_CLASS(_Object_Parameters, _SINGLE_DEST_REGISTER_INSTRUCTION):

    def opcode(self):
        return "const-class"
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.value_arg)


class MONITOR_ENTER(_SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "monitor-enter"
        
class MONITOR_EXIT(_SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "monitor-exit"
    
    
class CHECK_CAST( _Object_Parameters, _SINGLE_DEST_REGISTER_INSTRUCTION): 
    def opcode(self):
        return "check-cast"
         
        
class INSTANCE_OF(SmaliAssemblyInstruction):
    def __init__(self, reg_res, reg_arg, type_id):
        self.rr = SmaliRegister(reg_res)
        self.ra = SmaliRegister(reg_arg)
        self.type_id = type_id
        
    def get_registers(self):
        return [self.rr, self.ra]
        
    def opcode(self):
        return "instance-of"
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rr) + ", " + str(self.ra) + ", " + str(self.type_id)
        
    def get_register_type_implications(self):
        return {self.rr: SmaliTypes.ThirtyTwoBit(), self.ra: SmaliTypes.NonSpecificObjectReference()}
        

class NEW_INSTANCE(SmaliAssemblyInstruction):
    def __init__(self, reg_dest, type_id):
        self.rd = SmaliRegister(reg_dest)
        self.type_id = type_id
        
    def get_registers(self):
        return [self.rd]
            
    def opcode(self):
        return "new-instance"
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.type_id)
        
    def get_register_type_implications(self):
        return {self.rd: SmaliTypes.from_string(self.type_id)}
        


class ARRAY_LENGTH(SmaliAssemblyInstruction):
    def __init__(self, reg_dest, reg_array_ref):
        self.rd = SmaliRegister(reg_dest)
        self.rar = SmaliRegister(reg_array_ref)
        
    def get_registers(self):
        return [self.rd, self.rar]
        
    def opcode(self):
        return "array-length"
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.rar)
    
    def get_register_type_implications(self):
        return {self.rar: SmaliTypes.NonSpecificArray(), self.rd: SmaliTypes.ThirtyTwoBit()}    
    
        
class NEW_ARRAY(SmaliAssemblyInstruction):
    def __init__(self, reg_dest, reg_size, type_id):
        self.rd = SmaliRegister(reg_dest)
        self.rs = SmaliRegister(reg_size)
        self.type_id = type_id
        
    def get_registers(self):
        return [self.rd, self.rs]
        
    def opcode(self):
        return "new-array"
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.rs) + ", " + str(self.type_id)   
        
    def get_register_type_implications(self):
        return {self.rd: SmaliTypes.Array(self.type_id), self.rs: SmaliTypes.ThirtyTwoBit()}
        

class _PARAMETER_LIST_INSTRUCTION(SmaliAssemblyInstruction):
    # Not an ImplicitRegistersInstruction because both registers
    # for a wide-type will be explicitly listed in the parameter list
    def __init__(self, element_list, type_id):
        self.register_list = [SmaliRegister(r) for r in element_list]
        self.type_id = type_id

    def get_registers(self):
        return self.register_list

    def __repr__(self):
        string_register_list = [str(x) for x in self.register_list]
        reg_string = ", ".join(string_register_list)
        return self.opcode() + " {" + reg_string + "}, " + str(self.type_id)
        
        
class _PARAMETER_RANGE_INSTRUCTION(SmaliAssemblyInstruction):
    # Not an ImplicitRegistersInstruction because both registers
    # for a wide-type will be explicitly listed in the parameter list
    def __init__(self, element_list, signature):
        self.begin_reg = SmaliRegister(element_list[0])
        self.end_reg = SmaliRegister(element_list[-1])
        self.sig = signature
        
    def get_registers(self):
        
        if(self.begin_reg.letter() != "v" or self.end_reg.letter() != "v"):
            raise ValueError("Cannot expand register range [" + str(self))
        
        ans = []
        for x in range(self.begin_reg.number(), self.end_reg.number()+1):
            sr = SmaliRegister.from_components("v", x)
            ans.append(sr)
            
        return ans
        
        
    def __repr__(self):
        return self.opcode() + " {" + str(self.begin_reg) + " .. " + str(self.end_reg) + "}, " + str(self.sig)


class FILLED_NEW_ARRAY(_PARAMETER_LIST_INSTRUCTION):
    def opcode(self):
        return "filled-new-array"
        
    def get_register_type_implications(self):
        ans = {}
        for reg in self.get_registers():
            ans[reg] = SmaliTypes.from_string(self.type_id)
        return ans
        

class FILLED_NEW_ARRAY_RANGE(_PARAMETER_RANGE_INSTRUCTION):
    def opcode(self):
        return "filled-new-array/range"
        
    def get_register_type_implications(self):
        array_content_type = SmaliTypes.from_string(self.sig).unwrap_layer()
        ans = {}
        for reg in self.get_registers():
            ans[reg] = array_content_type
        return ans
        

class FILL_ARRAY_DATA(_SINGLE_DEST_REGISTER_INSTRUCTION):
    def opcode(self):
        return "fill-array-data"
    
    def get_register_type_implications(self):
        return {self.rd: SmaliTypes.NonSpecificArray()}

class THROW(_SINGLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "throw"
    
    def get_register_type_implications(self):
        return {self.rd: SmaliTypes.NonSpecificObjectReference()}


class GOTO(SmaliAssemblyInstruction):
    def __init__(self, target):
        self.target = target
        
    def opcode(self):
        return "goto"

    def __repr__(self):
        return self.opcode() + " " + str(self.target)

class GOTO_16(GOTO):
    def opcode(self):
        return "goto/16"

class GOTO_32(GOTO):
    def opcode(self):
        return "goto/32"


class PACKED_SWITCH(_SINGLE_DEST_REGISTER_INSTRUCTION):
    # NOTE: there is ALSO a .packed-switch and .sparse-switch
    # compiler directive in smali
    # e.g., .packed-switch -0x9
    # this object implements the instruction packed-switch vX, :pswitch_data_Y
    # I'm not sure what type vX holds, maybe int?
    def opcode(self):
        return "packed-switch"

class SPARSE_SWITCH(_SINGLE_DEST_REGISTER_INSTRUCTION):
    def opcode(self):
        return "sparse-switch"


class _TRIPLE_REGISTER_INSTRUCTION(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    def __init__(self, reg_dest, reg_arg1, reg_arg2):
        self.rd = SmaliRegister(reg_dest)
        self.ra1 = SmaliRegister(reg_arg1)
        self.ra2 = SmaliRegister(reg_arg2)
        
    def get_registers(self):
        return [self.rd, self.ra1, self.ra2]
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.ra1) + ", " + str(self.ra2)
        
        
class CMPL_FLOAT( _ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "cmpl-float"
        
class CMPG_FLOAT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "cmpg-float"
        
class CMPL_DOUBLE(_TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "cmpl-double"
        
    def get_implicit_registers(self):
        regs = self.get_registers()
        ans = []
        for reg in regs[1:]:
            implicit_reg = reg + 1
            ans.append(implicit_reg)
        return ans
        
    def get_register_type_implications(self):
        ans = {}
        
        for reg in self.get_registers():
            ans[reg] = SmaliTypes.SixtyFourBit()
        for reg in self.get_implicit_registers():
            ans[reg] = SmaliTypes.SixtyFourBit_2()
            
        ans[self.rd] = SmaliTypes.ThirtyTwoBit()
        return ans
        
class CMPG_DOUBLE(_TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "cmpg-double"
    
    def get_implicit_registers(self):
        regs = self.get_registers()
        ans = []
        for reg in regs[1:]:
            implicit_reg = "v" + str(int(reg[1:])+1)
            ans.append(implicit_reg)
        return ans
        
    def get_register_type_implications(self):
        ans = {}
        
        for reg in self.get_registers():
            ans[reg] = SmaliTypes.SixtyFourBit()
        for reg in self.get_implicit_registers():
            ans[reg] = SmaliTypes.SixtyFourBit_2()
            
        ans[self.rd] = SmaliTypes.ThirtyTwoBit()
        return ans
        
class CMP_LONG(_TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "cmp-long"
        
    def get_implicit_registers(self):
        regs = self.get_registers()
        ans = []
        for reg in regs[1:]:
            implicit_reg = reg + 1
            ans.append(implicit_reg)
        return ans

    def get_register_type_implications(self):
        ans = {}
        
        for reg in self.get_registers():
            ans[reg] = SmaliTypes.SixtyFourBit()
        for reg in self.get_implicit_registers():
            ans[reg] = SmaliTypes.SixtyFourBit_2()
            
        ans[self.rd] = SmaliTypes.ThirtyTwoBit()
        return ans
        
class _TWO_REG_EQ(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    def __init__(self, reg_arg1, reg_arg2, target):
        self.ra1 = SmaliRegister(reg_arg1)
        self.ra2 = SmaliRegister(reg_arg2)
        self.target = target
        
    def get_registers(self):
        return [self.ra1, self.ra2]
        
    def __repr__(self):
        return self.opcode() + " " + str(self.ra1) + ", " + str(self.ra2) + ", " + str(self.target)
        
class IF_EQ(_TWO_REG_EQ):
    def opcode(self):
        return "if-eq"
        
class IF_NE(_TWO_REG_EQ):
    def opcode(self):
        return "if-ne"
        
class IF_LT(_TWO_REG_EQ):
    def opcode(self):
        return "if-lt"
        
class IF_GE(_TWO_REG_EQ):
    def opcode(self):
        return "if-ge"
        
class IF_GT(_TWO_REG_EQ):
    def opcode(self):
        return "if-gt"
        
class IF_LE(_TWO_REG_EQ):
    def opcode(self):
        return "if-le"
        
        
class _ONE_REG_EQ_ZERO(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    def __init__(self, reg_arg, target):
        self.ra = SmaliRegister(reg_arg)
        self.target = target
        
    def get_registers(self):
        return [self.ra]
        
    def __repr__(self):
        # It might be necessary to use repr(self.target)
        # here because self.target might be a smali.LABEL
        # object or it might be a string.  
        
        # If it is a smali.LABEL object
        # then we use repr to get a string that does not contain
        # the preceding four spaces and trailing \n which would be 
        # redundant LABELS are weird because it is possible to use a 
        # LABEL in-line
        
        # This could be a bug in other classes, maybe re-write 
        # the LABEL(SmaliAssemblyInstruction) class
        return self.opcode() + " " + str(self.ra) + ", " + str(self.target)
        

class IF_EQZ(_ONE_REG_EQ_ZERO):
    def opcode(self):
        return "if-eqz"
        
class IF_NEZ(_ONE_REG_EQ_ZERO):
    def opcode(self):
        return "if-nez"

class IF_LTZ(_ONE_REG_EQ_ZERO):
    def opcode(self):
        return "if-ltz"
        
class IF_GEZ(_ONE_REG_EQ_ZERO):
    def opcode(self):
        return "if-gez"
        
class IF_GTZ(_ONE_REG_EQ_ZERO):
    def opcode(self):
        return "if-gtz"
        
class IF_LEZ(_ONE_REG_EQ_ZERO):
    def opcode(self):
        return "if-lez"     

        
class _Array_Parameters_Type_Pattern():
    def get_register_type_implications(self):
        # aget vX, vY, vZ
        # vX dest (or src for aput-* instructions)
        # vY a reference to an array
        # vZ index / offset into array (I think this must be a 32-bit int)
    
        self.ans = {}
        self.ans[self.ra1] = SmaliTypes.NonSpecificArray()
        self.ans[self.ra2] = SmaliTypes.Int()
        
        # this should be done last for situations such as
        # aget v4, v4, v6
        # where self.rd should definitely have final decision
        # about the type of v4
        self._set_first_param_type() 
        return self.ans
        
        
class AGET(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aget"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.ThirtyTwoBit()

class AGET_WIDE(_Array_Parameters_Type_Pattern, _ImplicitFirstRegisterInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aget-wide"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.SixtyFourBit()
        self.ans[StigmaStringParsingLib.register_addition(self.rd, 1)] = SmaliTypes.SixtyFourBit_2()

class AGET_OBJECT(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aget-object"
        
    def _set_first_param_type(self):
        # this is a special case and should be treated as such!
        # it really should check the type of vY and do an unwrap_layer()
        # but that's not possible in this class / context
        # because we don't have a register_type_map
        #
        # NonSpecificObjectReference as a very low specificity level
        self.ans[self.rd] = SmaliTypes.NonSpecificObjectReference()

class AGET_BOOLEAN(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aget-boolean"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Boolean()

class AGET_BYTE(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aget-byte"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Byte()

class AGET_CHAR(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aget-char"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Char()

class AGET_SHORT(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aget-short"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Short()


class APUT(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    # aput vX, vY, vZ
    # vX is a value to be put into the array
    # vY is an array reference
    # vZ is an index into that array
    def opcode(self):
        return "aput"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Int()

class APUT_WIDE(_Array_Parameters_Type_Pattern, _ImplicitFirstRegisterInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aput-wide"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.SixtyFourBit()
        self.ans[self.rd + 1] = SmaliTypes.SixtyFourBit_2()

class APUT_OBJECT(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aput-object"

    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.NonSpecificObjectReference()

class APUT_BOOLEAN(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aput-boolean"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Boolean()

class APUT_BYTE(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aput-byte"

    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Byte()

class APUT_CHAR(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aput-char"

    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Char()

class APUT_SHORT(_Array_Parameters_Type_Pattern, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "aput-short"
        
    def _set_first_param_type(self):
        self.ans[self.rd] = SmaliTypes.Short()





class _I_INSTRUCTION(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    #   Backward compatibility with how we call IGET() in Instrument
    # instance_field_name
    def __init__(self, reg_dest, reg_calling_instance, class_name , instance_field_name = ""): 
        #print("reg dest: ", reg_dest, "  reg_calling_instance", reg_calling_instance, "  class name", class_name, "  instance_field_name:", instance_field_name)
        self.rd = SmaliRegister(reg_dest)
        self.rci = SmaliRegister(reg_calling_instance)
        
        if instance_field_name != "":
            self.class_name = class_name
            ifn = instance_field_name
            self.class_and_field_name =  cn + "->" + ifn
        else:
            self.class_name = class_name.split("->")[0]
            self.class_and_field_name = class_name

        
    def get_registers(self):
        return [self.rd, self.rci]
        
    def get_register_type_implications(self):
        # iget vX, vY, type_id
        # vX dest (or src for iput-* instructions)
        # vY a reference to an object
        # vZ index / offset into array (I think this must be a 32-bit int)
    
        self.ans = {}
        
        tmp = self.class_and_field_name.split(":")[1]
        first_reg_type = SmaliTypes.from_string(tmp)  
        self.ans[self.rd] = first_reg_type
        self.ans[self.rci] = SmaliTypes.from_string(self.class_name)
        return self.ans

    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.rci) + ", " + self.class_and_field_name

class IGET(_I_INSTRUCTION):
    def opcode(self):
        return "iget"

        
class IGET_WIDE(_ImplicitFirstRegisterInstruction, _I_INSTRUCTION):
    def opcode(self):
        return "iget-wide"
        
    def get_register_type_implications(self):
        ans = super().get_register_type_implications()
        adj_reg = self.rd + 1
        ans[adj_reg] = SmaliTypes.SixtyFourBit_2()
        return ans
        
class IGET_OBJECT(_I_INSTRUCTION):
    def opcode(self):
        return "iget-object"

class IGET_BOOLEAN(_I_INSTRUCTION):
    def opcode(self):
        return "iget-boolean"

class IGET_BYTE(_I_INSTRUCTION):
    def opcode(self):
        return "iget-byte"

class IGET_CHAR(_I_INSTRUCTION):
    def opcode(self):
        return "iget-char"

class IGET_SHORT(_I_INSTRUCTION):
    def opcode(self):
        return "iget-short"

class IPUT(_I_INSTRUCTION):
    def opcode(self):
        return "iput"
        
class IPUT_WIDE(_ImplicitFirstRegisterInstruction, _I_INSTRUCTION):
    def opcode(self):
        return "iput-wide"
        
    def get_register_type_implications(self):
        ans = super().get_register_type_implications()
        adj_reg = self.rd + 1
        ans[adj_reg] = SmaliTypes.SixtyFourBit_2()
        return ans
        
class IPUT_OBJECT(_I_INSTRUCTION):
    def opcode(self):
        return "iput-object"

class IPUT_BOOLEAN(_I_INSTRUCTION):
    def opcode(self):
        return "iput-boolean"

class IPUT_BYTE(_I_INSTRUCTION):
    def opcode(self):
        return "iput-byte"

class IPUT_CHAR(_I_INSTRUCTION):
    def opcode(self):
        return "iput-char"

class IPUT_SHORT(_I_INSTRUCTION):
    def opcode(self):
        return "iput-short"


class _S_INSTRUCTION(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    #   Backward compatibility with how we call IGET() in Instrument
    def __init__(self, reg_dest, class_name , instance_field_name = ""): 
        self.field_fqn = ""
        self.rd = SmaliRegister(reg_dest)
        if instance_field_name != "":
            self.class_name = class_name
            ifn = instance_field_name
            self.class_and_field_name =  class_name + "->" + ifn
        else:
            self.class_and_field_name = class_name
        
    def get_registers(self):
        return [self.rd]
        
    def get_register_type_implications(self):
        # sget vX, type_id
        # vX dest (or src for iput-* instructions)
        # vY a reference to an object
        # vZ index / offset into array (I think this must be a 32-bit int)
    
        self.ans = {}
        
        tmp = self.class_and_field_name.split(":")[1]
        first_reg_type = SmaliTypes.from_string(tmp)  
        self.ans[self.rd] = first_reg_type
        return self.ans

    def __repr__(self):
        if self.field_fqn == "":
            return self.opcode() + " " + str(self.rd) + ", " + self.class_and_field_name

class SGET(_S_INSTRUCTION):
    def opcode(self):
        return "sget"

class SGET_WIDE(_ImplicitRegistersInstruction, _S_INSTRUCTION):
    def opcode(self):
        return "sget-wide"

    def get_register_type_implications(self):
        ans = super().get_register_type_implications()
        adj_reg = StigmaStringParsingLib.register_addition(self.rd, 1)
        ans[adj_reg] = SmaliTypes.SixtyFourBit_2()
        return ans
        
class SGET_OBJECT(_S_INSTRUCTION):
    def opcode(self):
        return "sget-object"

class SGET_BOOLEAN(_S_INSTRUCTION):
    def opcode(self):
        return "sget-boolean"

class SGET_BYTE(_S_INSTRUCTION):
    def opcode(self):
        return "sget-byte"

class SGET_CHAR(_S_INSTRUCTION):
    def opcode(self):
        return "sget-char"

class SGET_SHORT(_S_INSTRUCTION):
    def opcode(self):
        return "sget-short"

class SPUT(_S_INSTRUCTION):
    def opcode(self):
        return "sput"
        
class SPUT_WIDE(_ImplicitRegistersInstruction, _S_INSTRUCTION):
    def opcode(self):
        return "sput-wide"
        
    def get_register_type_implications(self):
        ans = super().get_register_type_implications()
        adj_reg = StigmaStringParsingLib.register_addition(self.rd, 1)
        ans[adj_reg] = SmaliTypes.SixtyFourBit_2()
        return ans
        
class SPUT_OBJECT(_S_INSTRUCTION):
    def opcode(self):
        return "sput-object"

class SPUT_BOOLEAN(_S_INSTRUCTION):
    def opcode(self):
        return "sput-boolean"

class SPUT_BYTE(_S_INSTRUCTION):
    def opcode(self):
        return "sput-byte"

class SPUT_CHAR(_S_INSTRUCTION):
    def opcode(self):
        return "sput-char"

class SPUT_SHORT(_S_INSTRUCTION):
    def opcode(self):
        return "sput-short"


class INVOKE_VIRTUAL(_PARAMETER_LIST_INSTRUCTION):
    # I was too lazy to implement the get_register_type_implications
    # function for the below instructions
    # It could be done with the SmaliSignature class from SmaliMethodDef.py
    def opcode(self):
        return "invoke-virtual"

class INVOKE_SUPER(_PARAMETER_LIST_INSTRUCTION):
    def opcode(self):
        return "invoke-super"

class INVOKE_DIRECT(_PARAMETER_LIST_INSTRUCTION):
    def opcode(self):
        return "invoke-direct"

class INVOKE_STATIC(_PARAMETER_LIST_INSTRUCTION):
    def opcode(self):
        return "invoke-static"

class INVOKE_INTERFACE(_PARAMETER_LIST_INSTRUCTION):
    def opcode(self):
        return "invoke-interface"

class INVOKE_VIRTUAL(_PARAMETER_LIST_INSTRUCTION):
    def opcode(self):
        return "invoke-virtual"

class INVOKE_VIRTUAL_RANGE(_PARAMETER_RANGE_INSTRUCTION):
    def opcode(self):
        return "invoke-virtual/range"

class INVOKE_SUPER_RANGE(_PARAMETER_RANGE_INSTRUCTION):
    def opcode(self):
        return "invoke-virtual/range"

class INVOKE_DIRECT_RANGE(_PARAMETER_RANGE_INSTRUCTION):
    def opcode(self):
        return "invoke-direct/range"

class INVOKE_STATIC_RANGE(_PARAMETER_RANGE_INSTRUCTION):
    def opcode(self):
        return "invoke-static/range"

class INVOKE_INTERFACE_RANGE(_PARAMETER_RANGE_INSTRUCTION):
    def opcode(self):
        return "invoke-interface/range"


class _TWO_REGISTER_UNARY_INSTRUCTION(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    def __init__(self, reg_dest, reg_arg):
        super().__init__()
        self.rd = SmaliRegister(reg_dest)
        self.ra = SmaliRegister(reg_arg)

    def get_registers(self):
        return [self.rd, self.ra]

    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.ra)


class NEG_INT(_ThirtyTwoBit_Parameters, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "neg-int"

class NOT_INT(_ThirtyTwoBit_Parameters, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "not-int"

class NEG_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "neg-long"

class NEG_FLOAT(_ThirtyTwoBit_Parameters, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "neg-float"

class NEG_DOUBLE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "neg-double"

class INT_TO_LONG(_ImplicitFirstRegisterInstruction, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "int-to-long"
        
    def get_register_type_implications(self):
        # annoying edge-case: int-to-long v5, v5
        ans = {self.rd: SmaliTypes.Long()}
        adj_reg = self.rd + 1
        ans[adj_reg] = SmaliTypes.Long_2()
        return ans
        

class INT_TO_FLOAT(_ThirtyTwoBit_Parameters, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "int-to-float"

class INT_TO_DOUBLE(_ImplicitFirstRegisterInstruction, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "int-to-double"
        
    def get_register_type_implications(self):
        ans = {self.rd: SmaliTypes.Double(), self.ra: SmaliTypes.Int()}
        adj_reg = StigmaStringParsingLib.register_addition(self.rd, 1)
        ans[adj_reg] = SmaliTypes.Double_2()
        return ans

class LONG_TO_INT(_TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "long-to-int"

    def get_implicit_registers(self):
        regs = self.get_registers()
        return [regs[1] + 1]
        
    def get_register_type_implications(self):
        ans = {self.rd: SmaliTypes.Int(), self.ra: SmaliTypes.Long()}
        adj_reg = StigmaStringParsingLib.register_addition(self.ra, 1)
        ans[adj_reg] = SmaliTypes.Long_2()
        return ans

class LONG_TO_FLOAT(_TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "long-to-float"
        
    def get_implicit_registers(self):
        regs = self.get_registers()
        return ["v" + str(int(regs[1][1:])+1)]
        
    def get_register_type_implications(self):
        ans = {self.rd: SmaliTypes.Float(), self.ra: SmaliTypes.Long()}
        adj_reg = StigmaStringParsingLib.register_addition(self.ra, 1)
        ans[adj_reg] = SmaliTypes.Long_2()
        return ans

class LONG_TO_DOUBLE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "long-to-double"


class FLOAT_TO_INT(_ThirtyTwoBit_Parameters, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "float-to-int"

class FLOAT_TO_LONG(_ImplicitFirstRegisterInstruction, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "float-to-long"
        
    def get_register_type_implications(self):
        ans = {self.rd: SmaliTypes.Long(), self.ra: SmaliTypes.Float()}
        adj_reg = StigmaStringParsingLib.register_addition(self.rd, 1)
        ans[adj_reg] = SmaliTypes.Long_2()
        return ans

class FLOAT_TO_DOUBLE(_ImplicitFirstRegisterInstruction, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "float-to-double"
        
    def get_register_type_implications(self):
        ans = {self.rd: SmaliTypes.Double(), self.ra: SmaliTypes.Float()}
        adj_reg = StigmaStringParsingLib.register_addition(self.rd, 1)
        ans[adj_reg] = SmaliTypes.Double_2()
        return ans

class DOUBLE_TO_INT(_TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "double-to-int"
        
    def get_implicit_registers(self):
        regs = self.get_registers()
        return ["v" + str(int(regs[1][1:])+1)]
        
    def get_register_type_implications(self):
        ans = {self.rd: SmaliTypes.Int(), self.ra: SmaliTypes.Double()}
        adj_reg = StigmaStringParsingLib.register_addition(self.ra, 1)
        ans[adj_reg] = SmaliTypes.Double_2()
        return ans

class DOUBLE_TO_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "double-to-long"

class DOUBLE_TO_FLOAT(_TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "double-to-float"
        
    def get_implicit_registers(self):
        regs = self.get_registers()
        return ["v" + str(int(regs[1][1:])+1)]
        
    def get_register_type_implications(self):
        ans = {self.rd: SmaliTypes.Float(), self.ra: SmaliTypes.Double()}
        adj_reg = StigmaStringParsingLib.register_addition(self.ra, 1)
        ans[adj_reg] = SmaliTypes.Double_2()
        return ans

class INT_TO_BYTE(_ThirtyTwoBit_Parameters, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "int-to-byte"

class INT_TO_CHAR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "int-to-char"

class INT_TO_SHORT(_ThirtyTwoBit_Parameters, _TWO_REGISTER_UNARY_INSTRUCTION):
    def opcode(self):
        return "int-to-short"

class ADD_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "add-int"

class SUB_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "sub-int"
        
class RSUB_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "rsub-int"

class MUL_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "mul-int"

class DIV_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "div-int"

class REM_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "rem-int"

class AND_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "and-int"

class OR_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "or-int"

class XOR_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "xor-int"

class SHL_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "shl-int"

class SHR_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "shr-int"

class USHR_INT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "ushr-int"

class ADD_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "add-long"

class SUB_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "sub-long"

class MUL_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "mul-long"

class DIV_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "div-long"

class REM_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "rem-long"

class AND_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "and-long"

class OR_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "or-long"

class XOR_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "xor-long"

class SHL_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "shl-long"

class SHR_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction,_TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "shr-long"

class USHR_LONG(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "ushr-long"

class ADD_FLOAT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "add-float"

class SUB_FLOAT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "sub-float"

class MUL_FLOAT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "mul-float"

class DIV_FLOAT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "div-float"

class REM_FLOAT(_ThirtyTwoBit_Parameters, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "rem-float"

class ADD_DOUBLE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "add-double"

class SUB_DOUBLE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "sub-double"

class MUL_DOUBLE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "mul-double"

class DIV_DOUBLE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "div-double"

class REM_DOUBLE(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TRIPLE_REGISTER_INSTRUCTION):
    def opcode(self):
        return "rem-double"


class _TWO_REGISTER_BINARY_INSTRUCTION(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    
    def __init__(self, reg_dest_and_arg1, reg_arg2):
        super().__init__()
        self.rd = SmaliRegister(reg_dest_and_arg1)
        self.ra1 = SmaliRegister(reg_dest_and_arg1)
        self.ra2 = SmaliRegister(reg_arg2)
        
    def get_registers(self):
        return [self.rd, self.ra2]
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.ra2)
    
    
class ADD_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "add-int/2addr"

class SUB_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "sub-int/2addr"

class MUL_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "mul-int/2addr"

class DIV_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "div-int/2addr"
        
class REM_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "rem-int/2addr"

class AND_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "and-int/2addr"
        
class OR_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "or-int/2addr"

class XOR_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "xor-int/2addr"

class SHL_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "shl-int/2addr"

class SHR_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "shr-int/2addr"

class USHR_INT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "ushr-int/2addr"
            
class ADD_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "add-long/2addr"

class SUB_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "sub-long/2addr"

class MUL_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "mul-long/2addr"

class DIV_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "div-long/2addr"
        
class REM_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "rem-long/2addr"

class AND_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "and-long/2addr"
        
class OR_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "or-long/2addr"

class XOR_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "xor-long/2addr"

class SHL_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "shl-long/2addr"

class SHR_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "shr-long/2addr"

class USHR_LONG_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "ushr-long/2addr"

class ADD_FLOAT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "add-float/2addr"
        
class SUB_FLOAT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "sub-float/2addr"
        
class MUL_FLOAT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "mul-float/2addr"
        
class DIV_FLOAT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "div-float/2addr"
        
class REM_FLOAT_2ADDR(_ThirtyTwoBit_Parameters, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "rem-float/2addr"
        
class ADD_DOUBLE_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "add-double/2addr"
        
class SUB_DOUBLE_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "sub-double/2addr"
        
class MUL_DOUBLE_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "mul-double/2addr"
        
class DIV_DOUBLE_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "div-double/2addr"
        
class REM_DOUBLE_2ADDR(_SixtyFourBit_Dest, _ImplicitRegistersInstruction, _TWO_REGISTER_BINARY_INSTRUCTION):
    def opcode(self):
        return "rem-double/2addr"
        

class _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    
    def __init__(self, reg_dest_and_arg1, reg_arg2, literal):
        self.rd = SmaliRegister(reg_dest_and_arg1)
        self.ra1 = SmaliRegister(reg_dest_and_arg1)
        self.ra2 = SmaliRegister(reg_arg2)
        self.lit = literal
        
    def get_registers(self):
        return [self.rd, self.ra2]
        
    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.ra2) + ", " + str(self.lit)


class ADD_INT_LIT16(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "add-int/lit16"
        
class SUB_INT_LIT16(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "sub-int/lit16"

class MUL_INT_LIT16(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "mul-int/lit16"
        
class DIV_INT_LIT16(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "div-int/lit16"
        
class REM_INT_LIT16(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "rem-int/lit16"

class AND_INT_LIT16(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "and-int/lit16"

class OR_INT_LIT16(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "or-int/lit16"
        
class XOR_INT_LIT16(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "xor-int/lit16"
        
class ADD_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "add-int/lit8"
        
class SUB_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "sub-int/lit8"
        
class RSUB_INT_LIT(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcodE(self):
        return "rsub-int/lit8"
        
class MUL_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "mul-int/lit8"
        
class DIV_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "div-int/lit8"
        
class REM_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "rem-int/lit8"
        
class AND_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "and-int/lit8"
        
class OR_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "or-int/lit8"
        
class XOR_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "xor-int/lit8"
        
class SHL_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "shl-int/lit8"
        
class SHR_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "shr-int/lit8"
        
class USHR_INT_LIT8(_ThirtyTwoBit_Parameters, _TWO_REGISTER_AND_LITERAL_BINARY_INSTRUCTION):
    def opcode(self):
        return "ushr-int/lit8"
        

        
        
class _I_INSTRUCTION_QUICK(SmaliAssemblyInstruction):
    # A parent class that should never be instantiated directly
    # No instances of any "quick" instruction found in our APKs
    def __init__(self, reg_dest, reg_calling_instance, offset): 
        self.rd = SmaliRegister(reg_dest)
        self.rci = SmaliRegister(reg_calling_instance)
        self.offset = offset
        
    def get_registers(self):
        return [self.rd, self.rci]
        
    def get_register_type_implications(self):
        # iget vX, vY, [offset value]
        # vX dest (or src for iput-* instructions)
        # vY a reference to an object
        self.ans = {self.rd: SmaliTypes.ThirtyTwoBit(), self.rci: SmaliTypes.NonSpecificObjectReference()}
        return self.ans

    def __repr__(self):
        return self.opcode() + " " + str(self.rd) + ", " + str(self.rci) + ", " + str(self.offset)

class IGET_QUICK(_I_INSTRUCTION_QUICK):
    def opcode(self):
        return "iget-quick"

class IGET_WIDE_QUICK(_SixtyFourBit_Dest, _ImplicitFirstRegisterInstruction, _I_INSTRUCTION_QUICK):
    def opcode(self):
        return "iget-wide-quick"
        
class IGET_OBJECT_QUICK(_Object_Parameters, _I_INSTRUCTION_QUICK):
    def opcode(self):
        return "iget-object-quick"
        
class IPUT_QUICK(_I_INSTRUCTION_QUICK):
    def opcode(self):
        return "iput-quick"
        
class IPUT_WIDE_QUICK(_SixtyFourBit_Dest, _ImplicitFirstRegisterInstruction, _I_INSTRUCTION_QUICK):
    def opcode(self):
        return "iput-wide-quick"
        
class IPUT_OBJECT_QUICK(_Object_Parameters, _I_INSTRUCTION_QUICK):
    def opcode(self):
        return "iput-object-quick"

class INVOKE_VIRTUAL_QUICK(_PARAMETER_LIST_INSTRUCTION):
    def __init__(self, element_list, vtable):
        super().__init__(element_list, None)
        self.vtable = vtable
        self.calling_object = SmaliRegister(element_list[0])
        
    def opcode(self):
        return "invoke-virtual-quick"
        
    def __repr__(self):
        reg_string = ", ".join([str(r) for r in self.register_list])
        return self.opcode() + " {" + reg_string + "}, " + str(self.vtable)

class INVOKE_SUPER_QUICK(_PARAMETER_LIST_INSTRUCTION):
    def __init__(self, element_list, vtable):
        super().__init__(element_list, None)
        self.vtable = vtable
        self.calling_object = SmaliRegister(element_list[0])
        
    def opcode(self):
        return "invoke-super-quick"
        
    def __repr__(self):
        reg_string = ", ".join(self.register_list)
        return self.opcode() + " {" + reg_string + "}, " + str(self.vtable)


# The following classes don't seem to
# appear anywhere in our APK files
# so they are left unimplemented
# class INVOKE_VIRTUAL_QUICK_RANGE
# class INVOKE_SUPER_QUICK_RANGE
        
class LABEL(SmaliAssemblyInstruction):
    def __init__(self, num):
        self.n = num

    def __repr__(self):
        # LABELS are weird.  If you change this code be careful of compatibility 
        # with instructions such as IF_EQZ that use a LABEL in-line
        return ":stigma_jump_label_" + str(self.n)


class LOG_D(INVOKE_STATIC):
    # Not actually an assembly instruction!  More 
    # of a short-cut to quickly create an instance
    # of invoke-static for a Log.d() call
    def __init__(self, reg_tag, reg_msg):
        self.rt = SmaliRegister(reg_tag)
        self.rm = SmaliRegister(reg_msg)

    def __repr__(self):
        return "invoke-static {" + str(self.rt) + ", " + str(self.rm) + "},  Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I"



TYPE_CODE_WORD = 0
TYPE_CODE_WIDE = 1
TYPE_CODE_WIDE_REMAINING = 2
TYPE_CODE_OBJ_REF = 3

TYPE_CODE_ALL = [TYPE_CODE_WORD, TYPE_CODE_WIDE, 
    TYPE_CODE_WIDE_REMAINING, TYPE_CODE_OBJ_REF]

# https://github.com/JesusFreke/smali/wiki/TypesMethodsAndFields
TYPE_LIST_OBJECT_REF = ["L", "["]
TYPE_LIST_WIDE = ["J", "D"]
TYPE_LIST_WIDE_REMAINING = ["J2", "D2"]
TYPE_LIST_WORD = ["Z", "B", "S", "C", "I", "F"]

TYPE_LIST_ALL = TYPE_LIST_OBJECT_REF \
                    + TYPE_LIST_WIDE \
                    + TYPE_LIST_WIDE_REMAINING \
                    + TYPE_LIST_WORD


def type_code_name(type_code):
    if(type_code == None):
        return "None"
    elif(type_code == TYPE_CODE_WORD):
        return "TYPE_WORD"
    elif(type_code == TYPE_CODE_OBJ_REF):
        return "TYPE_OBJ_REF"
    elif(type_code == TYPE_CODE_WIDE):
        return "TYPE_WIDE"
    elif(type_code == TYPE_CODE_WIDE_REMAINING):
        return "TYPE_WIDE_REM"
    else:
        raise ValueError("Invalid Type Code: " + str(type_code))






def opcode_has_parameter_list(opcode):
    return opcode in ["filled-new-array", "invoke-virtual", "invoke-super", "invoke-direct",
        "invoke-static", "invoke-interface", "execute-inline", "invoke-virtual-quick", 
        "invoke-super-quick"]


def opcode_has_parameter_range(opcode):
    return opcode.endswith("/range")


def main():

    # One test for every isntruction in SmaliAssemblyInstructions.py
    # http://pallergabor.uw.hu/androidblog/dalvik_opcodes.html
    
    print("Testing SmaliAssemblyInstructions")

    # second line is intentionally a blank line
    TESTS = ["    nop\n",
             "    \n",
             "    move v6, p5\n",
             "    move/16 v6, v24\n", # synthetic example
             "    move/from16 v5, v26\n",
             "    move-wide v14, v7\n",
             "    move-wide/from16 v15, p3\n",
             "    move-wide/16 v12, p2\n", # synthetic example
             "    move-object v4, v3\n",
             "    move-object/from16 v5, v31\n",
             "    move-object/16 v2, v3\n", # synthetic example
             "    move-result v0\n", 
             "    move-result-wide v3\n",
             "    move-result-object v3\n",
             "    move-exception v0\n",
             "    return-void\n",
             "    return-wide v0\n",
             "    return-object v1\n",
             "    const v3, 0xffff\n",
             "    const/4 v1, -0x1\n",
             "    const/16 v0, 0xb\n",
             "    const/high16 v3, 0x3f800000\n", # 0xf800... is float value 1.0
             "    const-wide/16 v18, 0x1\n",
             "    const-wide/32 v6, 0x2932e00\n",
             "    const-wide v4, 0x100000000L\n",
             "    const-wide/high16 v2, -0x8000000000000000L\n",
             "    const-string v1, \"Parcelables cannot be written to an OutputStream\"\n",
             "    const-class v4, Landroidx/versionedparcelable/VersionedParcel;\n",
             "    monitor-enter p0\n",
             "    monitor-exit p0\n",
             "    check-cast v3, Ljava/lang/String;\n",
             "    instance-of v0, p1, Ljava/lang/Integer;\n",
             "    new-instance v0, Ljava/lang/RuntimeException;\n",
             "    array-length v0, p1\n",
             "    new-array v1, v0, [J\n",
             "    filled-new-array {v0, v1, v2}, [Ljava/lang/String;\n",
             #"    filled-new-array/range {v19..v21}, [B\n",
             "    fill-array-data v1, :array_6\n",
             "    throw v1\n",
             "    goto :goto_0\n",
             "    goto/32 :goto_0\n", # synthetic example
             "    goto/16 :goto_0\n",  # synthetic example
             "    packed-switch p1, :pswitch_data_0\n",
             "    sparse-switch v3, :sswitch_data_0\n",
             "    cmpl-float v5, v4, v6\n",
             "    cmpg-float v5, p1, v5\n",
             "    cmpl-double v16, v0, v14\n",
             "    cmpg-double v13, v8, v14\n",
             "    cmp-long v6, v4, p1\n",
             "    if-eq v3, v1, :cond_2\n",
             "    if-ne v1, p1, :cond_0\n",
             "    if-lt v3, v2, :cond_0\n",
             "    if-ge v1, v0, :cond_1\n",
             "    if-gt v12, v14, :cond_8\n",
             "    if-le v3, v10, :cond_25\n",
             "    if-eqz v4, :cond_0\n",
             "    if-nez v0, :cond_0\n",
             "    if-ltz v0, :cond_7\n",
             "    if-gez v0, :cond_0\n",
             "    if-gtz v5, :cond_0\n",
             "    if-lez v0, :cond_0\n",
             "    aget v0, v0, v1\n",
             "    aput v1, v0, v2\n",
             "    iget-object v0, p0, Landroidx/transition/TransitionSet$1;->val$nextTransition:Landroidx/transition/Transition;\n",
             "    iput p2, p0, Landroidx/transition/TransitionSet$1;->val$nextTransition:Landroidx/transition/Transition;\n",
             "    sget-wide v2, Lcom/google/android/material/card/MaterialCardViewHelper;->COS_45:D\n",
             "    sput-object v0, Lcom/google/android/material/snackbar/Snackbar;->SNACKBAR_BUTTON_STYLE_ATTR:[I\n",
             "    sput-boolean v0, Lcom/google/android/material/ripple/RippleUtils;->USE_FRAMEWORK_RIPPLE:Z\n",
             "    sput-char v0, Lcom/google/android/material/ripple/RippleUtils;->USE_FRAMEWORK_RIPPLE:Z\n", # synthetic
             "    invoke-virtual {v1, v2, p1}, Landroid/os/Bundle;->putParcelable(Ljava/lang/String;Landroid/os/Parcelable;)V\n",
             "    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V\n",
             "    invoke-super {p0}, Landroid/widget/GridView;->onAttachedToWindow()V\n",
             "    invoke-interface {v1}, Ljava/util/Collection;->iterator()Ljava/util/Iterator;\n",
             "    neg-int v2, v0\n",
             "    int-to-long v3, p1\n",
             "    long-to-int v7, v6\n",
             "    float-to-int v1, v1\n",
             "    double-to-float v3, v3\n",
             "    int-to-char v2, v2\n",
             "    add-int v0, v11, v13\n",
             "    or-int v6, v2, p2\n",
             "    div-double v2, p17, v2\n",
             "    add-int/2addr v3, v4\n",
             "    shl-int/2addr v7, v2\n",
             "    add-long/2addr v1, v3\n",
             "    add-float/2addr v6, v7\n",
             "    sub-double/2addr v11, v9\n",
             "    mul-int/lit16 v0, v0, 0x3e8\n",
             "    ushr-int/lit8 v2, v2, 0x1\n",
             "    iget-quick v1, v2, [obj+0010]\n", # not sure about this
             "    invoke-virtual-quick {v15, v12}, vtable\n", # not sure about this
    # New test cases can be added by (a) selecting an instruction
    # and then (b) grep-ing some smali for that instruction
    # e.g., suppose we're looking for an example of filled-new-array
    # grep -R -n "filled-new-array" ./apkOutput/*

    ]


    obj = NOP()
    #print("obj: ", obj)

    print("\tconstructor tests...")
    for cur_line in TESTS:
        #print("\t" + cur_line.strip())
        obj = SmaliAssemblyInstruction.from_line(cur_line)
        #print(type(obj), ": " + str(obj))
        assert(str(obj) == cur_line)
        

    rando_test = "invoke-direct/range {v6 .. v11}, Lcom/google/android/gms/common/data/DataHolder;-><init>(I[Ljava/lang/String;[Landroid/database/CursorWindow;ILandroid/os/Bundle;)V"
    obj = SmaliAssemblyInstruction.from_line(rando_test)
    #print(str(obj))
    #print(rando_test)
    assert(str(obj) == "    " + rando_test + "\n")


    print("\timplicit registers tests...")
    asm_obj = SmaliAssemblyInstruction.from_line("    move-wide v0, v15\n")
    #print(asm_obj)
    #print(asm_obj.get_registers())
    #print(asm_obj.get_implicit_registers())
    assert(asm_obj.get_registers() == ["v0", "v15"])
    assert(asm_obj.get_implicit_registers() == ["v1", "v16"])
    
    asm_obj = SmaliAssemblyInstruction.from_line("    cmpl-double v0, v1, v15\n")
    assert(asm_obj.get_registers() == ["v0", "v1", "v15"])
    assert(asm_obj.get_implicit_registers() == ["v2", "v16"])
    
    asm_obj = SmaliAssemblyInstruction.from_line("    cmp-long v2, v3, v5")
    assert(asm_obj.get_registers() == ["v2", "v3", "v5"])
    assert(asm_obj.get_implicit_registers() == ["v4", "v6"])
    
    asm_obj = SmaliAssemblyInstruction.from_line("    aget-wide v15, v1, v2\n")
    assert(asm_obj.get_registers() == ["v15", "v1", "v2"])
    assert(asm_obj.get_implicit_registers() == ["v16"])
    
    asm_obj = SmaliAssemblyInstruction.from_line("    iput-wide v2, v4, Ljava/lang/String;")
    assert(asm_obj.get_registers() == ["v2", "v4"])
    assert(asm_obj.get_implicit_registers() == ["v3"])
    
    asm_obj = SmaliAssemblyInstruction.from_line("    sget-wide v2, Ljava/lang/String;->length:J")
    assert(asm_obj.get_registers() == ["v2"])
    assert(asm_obj.get_implicit_registers() == ["v3"])
    
    asm_obj = SmaliAssemblyInstruction.from_line("    int-to-long v2, v4\n")
    assert(asm_obj.get_registers() == ["v2", "v4"])
    assert(asm_obj.get_implicit_registers() == ["v3"])
    
    asm_obj = SmaliAssemblyInstruction.from_line("    long-to-int v0, v15\n")
    assert(asm_obj.get_registers() == ["v0", "v15"])
    assert(asm_obj.get_implicit_registers() == ["v16"])
    
    
    
    #print("is targeted tests...")
    #asm_obj = SmaliAssemblyInstruction.from_line("    move-wide v0, v15\n")
    #assert(asm_obj.targeted_for_instrumentation == True)
    #asm_obj.targeted_for_instrumentation = False
    #assert(asm_obj.targeted_for_instrumentation == False)
    
    #asm_obj = SmaliAssemblyInstruction.from_line("    nop\n")
    #assert(asm_obj.targeted_for_instrumentation == False)
    #asm_obj.targeted_for_instrumentation = True
    #assert(asm_obj.targeted_for_instrumentation == True)
    
    print("\tregister type implication tests...")
    asm_obj = SmaliAssemblyInstruction.from_line("nop")
    assert(str(asm_obj.get_register_type_implications()) == '{}')
    
    asm_obj = SmaliAssemblyInstruction.from_line("    move v2, v3\n")
    #print(asm_obj.get_register_type_implications())
    assert(str(asm_obj.get_register_type_implications()) == "{v2: 32-bit, v3: 32-bit}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("    move-wide v4, v14\n")
    assert(str(asm_obj.get_register_type_implications()) == "{v4: 64-bit, v5: 64-bit-2}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("    move-wide/16 v10, v21")
    assert(str(asm_obj.get_register_type_implications()) == "{v10: 64-bit, v11: 64-bit-2}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("move-result-wide v22")
    assert(str(asm_obj.get_register_type_implications()) == "{v22: 64-bit, v23: 64-bit-2}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("move-object v0, v2")
    assert(str(asm_obj.get_register_type_implications()) == "{v0: Non Specific Object, v2: Non Specific Object}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("const-string v2, \"accessibility\"\n")
    assert(str(asm_obj.get_register_type_implications()) == "{v2: Ljava/lang/String;}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("new-instance v4, Landroid/widget/Scroller;")
    assert(str(asm_obj.get_register_type_implications()) == "{v4: Landroid/widget/Scroller;}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("aget v4, v4, v6")
    assert(str(asm_obj.get_register_type_implications()) == "{v4: 32-bit, v6: I}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("array-length v7, v7")
    #print(asm_obj.get_register_type_implications())
    assert(str(asm_obj.get_register_type_implications()) == "{v7: 32-bit}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("filled-new-array/range {v10 .. v16}, [Ljava/lang/String;\n")
    assert(str(asm_obj) == "    filled-new-array/range {v10 .. v16}, [Ljava/lang/String;\n")
    assert(str(asm_obj.get_register_type_implications()) == "{v10: Ljava/lang/String;, v11: Ljava/lang/String;, v12: Ljava/lang/String;, v13: Ljava/lang/String;, v14: Ljava/lang/String;, v15: Ljava/lang/String;, v16: Ljava/lang/String;}")
    assert(str(asm_obj.get_registers()) == "[v10, v11, v12, v13, v14, v15, v16]")
    
    asm_obj = SmaliAssemblyInstruction.from_line("aput-wide v2, v4, v6")
    assert(str(asm_obj.get_register_type_implications()) == "{v4: Non Specific Array, v6: I, v2: 64-bit, v3: 64-bit-2}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("iget-wide v3, v0, Landroid/HypotheticalClass;->MyDouble:D")
    assert(str(asm_obj) == "    iget-wide v3, v0, Landroid/HypotheticalClass;->MyDouble:D\n")
    #print(asm_obj.get_register_type_implications())
    assert(str(asm_obj.get_register_type_implications()) == "{v3: D, v0: Landroid/HypotheticalClass;, v4: 64-bit-2}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("iget-object v4, v2, Landroid/HypotheticalClass;->MyLoc:Landroid/location/LocationManager;")
    assert(str(asm_obj) == "    iget-object v4, v2, Landroid/HypotheticalClass;->MyLoc:Landroid/location/LocationManager;\n")
    assert(str(asm_obj.get_register_type_implications()) == "{v4: Landroid/location/LocationManager;, v2: Landroid/HypotheticalClass;}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("iput-object v2, v0, Ledu/fandm/enovak/leaks/Main;->MyString:Ljava/lang/String;")
    assert(str(asm_obj.get_register_type_implications()) == "{v2: Ljava/lang/String;, v0: Ledu/fandm/enovak/leaks/Main;}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("iput-wide v2, v0, Ledu/fandm/enovak/leaks/Main;->MyVal:J")
    assert(str(asm_obj.get_register_type_implications()) == "{v2: J, v0: Ledu/fandm/enovak/leaks/Main;, v3: 64-bit-2}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("sput-object v0, Ledu/fandm/enovak/leaks/Main;->TAG:Ljava/lang/String;")
    assert(str(asm_obj.get_register_type_implications()) == "{v0: Ljava/lang/String;}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("add-long v6, v0, v5")
    assert(str(asm_obj.get_register_type_implications()) == "{v6: 64-bit, v7: 64-bit-2}")
    
    asm_obj = SmaliAssemblyInstruction.from_line("int-to-long v0, v0")
    assert(str(asm_obj.get_register_type_implications()) == "{v0: J, v1: J2}")
    
    
    print("ALL SmaliAssemblyInstructions TESTS PASSED!")

# Do nothing if this file is called directly
# this is only a library
if __name__ == "__main__":
    main()
